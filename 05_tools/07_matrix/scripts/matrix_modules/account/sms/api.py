"""
短信验证码 — API 自动获取（wx.tyhtak.com）

代替手动输入，自动轮询 API 获取验证码。
"""
import asyncio
import re
import time
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError
import json

from .base import SMSHandler

API_KEY = "gtmsg2026"
PHONE = "15370103682"
BASE_URL = "https://wx.tyhtak.com/api/biz/msg/messages"


class ApiSMSHandler(SMSHandler):
    """通过 API 自动获取短信验证码"""

    def __init__(self, api_key: str = API_KEY, phone: str = PHONE):
        self.api_key = api_key
        self.phone = phone
        self._last_id: Optional[int] = None
        self._cancel_flag = False

    def _fetch_messages(self) -> list:
        """调用 API 获取短信列表"""
        url = f"{BASE_URL}?api_key={self.api_key}&receiver_phone={self.phone}&page=1&per_page=20"
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
        # 常见格式: 【平台】验证码556314，10分钟内有效。
        m = re.search(r'验证码[：:]\s*(\d{4,6})', content)
        if m:
            return m.group(1)
        m = re.search(r'验证码(\d{4,6})', content)
        if m:
            return m.group(1)
        # 兜底：提取4-6位纯数字（避免提取手机号等长数字）
        nums = re.findall(r'\b(\d{4,6})\b', content)
        if nums:
            # 优先取6位，其次4位
            for n in nums:
                if len(n) in (4, 6):
                    return n
        return None

    async def wait(self, platform: str = "", timeout: int = 120) -> str:
        """轮询 API 直到获取验证码或超时

        Args:
            platform: 平台名称（仅日志）
            timeout: 超时秒数

        Returns:
            验证码字符串，超时返回空字符串
        """
        print(f"  📱 等待短信验证码 ({platform})")
        print(f"    手机号: {self.phone}")
        print(f"    轮询间隔: 3秒  超时: {timeout}秒")

        self._cancel_flag = False
        self._last_id = None

        # 先获取当前最新消息 ID，避免取到旧消息
        msgs = self._fetch_messages()
        if msgs:
            self._last_id = max(m.get("id", 0) for m in msgs)
            print(f"    当前最新消息ID: {self._last_id}")

        start = time.time()
        while not self._cancel_flag and (time.time() - start) < timeout:
            await asyncio.sleep(3)

            msgs = self._fetch_messages()
            if not msgs:
                continue

            # 只检查比 last_id 新的消息
            for msg in msgs:
                msg_id = msg.get("id", 0)
                if self._last_id and msg_id <= self._last_id:
                    continue

                content = msg.get("content", "")
                code = self._extract_code(content)
                if code:
                    print(f"    ✅ 获取到验证码: {code}")
                    self._last_id = msg_id
                    return code

                # 没有验证码但也更新 last_id（避免重复处理）
                self._last_id = max(self._last_id or 0, msg_id)

            elapsed = int(time.time() - start)
            if elapsed % 15 < 3:  # 每 15 秒打印一次状态
                print(f"    ⏳ 等待中... ({elapsed}s / {timeout}s)")

        print(f"    ⏰ 超时 ({timeout}秒)，未获取到验证码")
        return ""

    async def cancel(self):
        """取消等待"""
        self._cancel_flag = True
        print("  ⏹ API 短信等待已取消")
