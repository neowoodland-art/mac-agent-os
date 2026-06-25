"""
短信验证码 — API 自动获取（wx.tyhtak.com）

代替手动输入，自动轮询 API 获取验证码。
配置从 ../config/sms.yaml 读取，不再硬编码。
"""
import asyncio
import re
import time
import os
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError
import json
import yaml

from .base import SMSHandler

# 默认值（会被 config/sms.yaml 覆盖）
API_KEY = "gtmsg2026"
PHONE = "15370103682"
BASE_URL = "https://wx.tyhtak.com/api/biz/msg/messages"
POLL_INTERVAL = 3
TIMEOUT = 120


def _load_config() -> dict:
    """从 config/sms.yaml 读取配置"""
    config_path = os.path.join(
        os.path.dirname(__file__),  # account/sms/
        "..", "..", "..", "..",     # → scripts/
        "config", "sms.yaml"
    )
    config_path = os.path.normpath(config_path)
    try:
        with open(config_path) as f:
            data = yaml.safe_load(f)
            return data.get("sms", {})
    except (FileNotFoundError, yaml.YAMLError):
        return {}


class ApiSMSHandler(SMSHandler):
    """通过 API 自动获取短信验证码"""

    def __init__(self, api_key: str = None, phone: str = None):
        cfg = _load_config()
        self.api_key = api_key or cfg.get("api_key", API_KEY)
        self.phone = phone or cfg.get("phone", PHONE)
        self.base_url = cfg.get("base_url", BASE_URL)
        self.poll_interval = cfg.get("poll_interval", POLL_INTERVAL)
        self.default_timeout = cfg.get("timeout", TIMEOUT)
        self._last_id: Optional[int] = None
        self._cancel_flag = False

    def _fetch_messages(self) -> list:
        """调用 API 获取短信列表"""
        url = f"{self.base_url}?api_key={self.api_key}&receiver_phone={self.phone}&page=1&per_page=20"
        try:
            req = Request(url, headers={"User-Agent": "curl/7.0"})
            resp = urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            if data.get("code") == 200:
                return data.get("data", {}).get("items", [])
            return []
        except (URLError, json.JSONDecodeError, Exception) as e:
            print(f"  ⚠️ API 请求失败: {e}")
            return []

    @staticmethod
    def _extract_code(content: str) -> Optional[str]:
        """从短信内容中提取验证码（4位或6位）

        匹配模式：验证码后跟4-6位数字
        """
        # 常见格式: 【平台】验证码556314 / 验证码，346758 / 验证码:729472
        m = re.search(r'验证码[：:，,]\s*(\d{4,6})', content)
        if m:
            return m.group(1)
        # 验证码直接跟数字（无分隔符）
        m = re.search(r'验证码(\d{4,6})', content)
        if m:
            return m.group(1)
        # 兜底：提取4-6位纯数字（避免提取手机号等长数字）
        nums = re.findall(r'\b(\d{4,6})\b', content)
        if nums:
            # 优先取6位，其次4位；排除明显的年份/月份
            for n in nums:
                if len(n) == 6 and n[0] != '2':  # 6位且不是年份
                    return n
            for n in nums:
                if len(n) in (4, 6) and n not in ('2024','2025','2026'):  # 排除年份
                    return n
        return None

    async def wait(self, platform: str = "", timeout: int = 120,
                   after_time: float = None) -> str:
        """轮询 API 直到获取验证码或超时

        Args:
            platform: 平台名称（仅日志）
            timeout: 超时秒数
            after_time: 只接受该时间戳之后到达的短信（time.time() 格式）

        Returns:
            验证码字符串，超时返回空字符串
        """
        print(f"  📱 等待短信验证码 ({platform})")
        print(f"    手机号: {self.phone}")
        print(f"    轮询间隔: {self.poll_interval}秒  超时: {timeout}秒")

        if after_time:
            print(f"    ⏱️  只接受 {datetime.fromtimestamp(after_time).strftime('%H:%M:%S')} 之后的短信")
        self._cancel_flag = False

        start = time.time()
        while not self._cancel_flag and (time.time() - start) < timeout:
            await asyncio.sleep(self.poll_interval)

            msgs = self._fetch_messages()
            if not msgs:
                continue

            for msg in msgs:
                # 用时间过滤：只接受 after_time 之后到达的消息
                if after_time:
                    msg_time_str = msg.get("created_at") or msg.get("time") or msg.get("send_time") or ""
                    if msg_time_str:
                        try:
                            from datetime import datetime
                            msg_ts = datetime.fromisoformat(msg_time_str.replace("Z", "+00:00")).timestamp()
                            if msg_ts <= after_time:
                                continue
                        except Exception:
                            pass  # 时间解析失败，不过滤

                content = msg.get("content", "")
                code = self._extract_code(content)
                if code:
                    print(f"    ✅ 获取到验证码: {code}")
                    return code

            elapsed = int(time.time() - start)
            if elapsed % 15 < 3:  # 每 15 秒打印一次状态
                print(f"    ⏳ 等待中... ({elapsed}s / {timeout}s)")

        print(f"    ⏰ 超时 ({timeout}秒)，未获取到验证码")
        return ""

    async def cancel(self):
        """取消等待"""
        self._cancel_flag = True
        print("  ⏹ API 短信等待已取消")
