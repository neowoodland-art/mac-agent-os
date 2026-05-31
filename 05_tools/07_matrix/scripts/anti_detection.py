#!/usr/bin/env python3
"""
AntiDetection — 反检测模块 (v1.0.0)

基于旧版完整手册 (IMPLEMENTATION_GUIDE.md) 提取的反检测措施。

功能:
  1. 浏览器指纹覆写 (webdriver/platform/standalone/plugins/languages)
  2. 拟人化行为参数 (随机延迟/观看时长/打字速度)
  3. 账号行为画像 (每小时操作上限)
  4. DOM弹窗清理 (扩展选择器列表)
"""

import asyncio
import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

__version__ = "1.0.0"

# ─── 浏览器指纹覆写脚本 ────────────────────────────────────────

FINGERPRINT_SCRIPT = """
() => {
    // 1. 隐藏自动化标记 (最关键)
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
    
    // 2. 平台与UA一致性
    Object.defineProperty(navigator, 'platform', { get: () => 'iPad' });
    
    // 3. 隐藏PWA安装能力
    Object.defineProperty(navigator, 'standalone', { get: () => false });
    
    // 4. 插件列表 (真实iPad有5个plugin)
    Object.defineProperty(navigator, 'plugins', { 
        get: () => [1, 2, 3, 4, 5] 
    });
    
    // 5. 语言设置
    Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh'] });
    
    // 6. 硬件并发数 (Apple M1 = 8)
    Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
    
    // 7. 设备内存 (iPad Pro = 8GB)
    Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
    
    // 8. 最大触控点 (iPad = 5)
    Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 5 });
    
    return 'fingerprint_applied';
}
"""

# ─── DOM弹窗清理脚本 (扩展版) ───────────────────────────────────

OVERLAY_REMOVE_SCRIPT = """
() => {
    const selectors = [
        // 下载/打开App弹窗
        '[class*="download"]', '[class*="open-app"]', '[class*="app-guide"]',
        '[class*="launch-app"]', '[class*="open-in-app"]', '[class*="app-launcher"]',
        '.open-in-app', '.app-launch-mask', '.download-tip', '.bottom-bar',
        '.download-banner', '.open-app-btn', '.app-download-tip',
        '.open-app-layer', '.download-guide-mask',
        '.open-in-app-bar', '.app-open-button',
        
        // 模态弹窗
        '#app-launch-dialog', '#open-app-modal', '#download-modal',
        '[class*="modal"]', '[class*="overlay"]', '[class*="mask"]',
        
        // 登录引导 (非登录页)
        '[class*="login-guide"]', '[class*="guide-layer"]',
        
        // 更新提示
        '[class*="update-tip"]', '[class*="upgrade"]',
        
        // 通用遮罩
        '[style*="position: fixed"][style*="z-index"]',
    ];
    let count = 0;
    selectors.forEach(s => {
        document.querySelectorAll(s).forEach(el => {
            // 不删除 video 标签
            if (el.tagName !== 'VIDEO') {
                el.remove();
                count++;
            }
        });
    });
    document.body.style.overflow = '';
    document.body.style.overflowY = 'auto';
    document.body.style.position = '';
    return count;
}
"""


# ─── 行为画像 ─────────────────────────────────────────────────

DEFAULT_PROFILE = {
    "action_delay_min": 0.8,         # 动作最小间隔(秒)
    "action_delay_max": 3.0,         # 动作最大间隔(秒)
    "view_duration_min": 5,          # 最小观看(秒)
    "view_duration_max": 30,         # 最大观看(秒)
    "typing_speed_ms": [80, 200],    # 打字速度(ms/字符)
    "max_likes_per_hour": 15,
    "max_collects_per_hour": 5,
    "max_comments_per_hour": 3,
    "max_follows_per_hour": 10,
    "max_daily_actions": 150,
    "active_hours": [8, 23],
}


class BehaviorProfile:
    """账号行为画像 — 控制操作频率和拟人化"""

    def __init__(self, account_id: str, custom: dict = None):
        self.account_id = account_id
        self.params = dict(DEFAULT_PROFILE)
        if custom:
            self.params.update(custom)
        self._action_count = 0
        self._hourly_counts = {}  # {action_type: count}
        self._session_start = time.time()

    def random_delay(self) -> float:
        """随机动作间隔"""
        return random.uniform(self.params["action_delay_min"],
                              self.params["action_delay_max"])

    def random_view_duration(self) -> int:
        """随机观看时长(秒)"""
        return random.randint(self.params["view_duration_min"],
                              self.params["view_duration_max"])

    async def human_type(self, page, text: str):
        """拟人化打字"""
        for char in text:
            delay = random.randint(*self.params["typing_speed_ms"]) / 1000
            await page.keyboard.type(char, delay=delay)

    async def random_wait(self):
        """随机等待（行为间隔）"""
        delay = self.random_delay()
        await asyncio.sleep(delay)

    def can_act(self, action_type: str) -> bool:
        """检查是否可以执行某种操作（频率限制）"""
        # 每日总量检查
        if self._action_count >= self.params["max_daily_actions"]:
            return False

        # 每小时频率检查
        current_hour = datetime.now().hour
        if current_hour < self.params["active_hours"][0] or \
           current_hour > self.params["active_hours"][1]:
            return False

        limits = {
            "like": self.params["max_likes_per_hour"],
            "collect": self.params["max_collects_per_hour"],
            "comment": self.params["max_comments_per_hour"],
            "follow": self.params["max_follows_per_hour"],
        }
        limit = limits.get(action_type, 100)
        hour_key = f"{action_type}_{datetime.now().hour}"
        if self._hourly_counts.get(hour_key, 0) >= limit:
            return False

        return True

    def record_action(self, action_type: str):
        """记录一次操作"""
        self._action_count += 1
        hour_key = f"{action_type}_{datetime.now().hour}"
        self._hourly_counts[hour_key] = self._hourly_counts.get(hour_key, 0) + 1

    def get_stats(self) -> dict:
        """获取当前会话统计"""
        return {
            "account": self.account_id,
            "session_seconds": int(time.time() - self._session_start),
            "total_actions": self._action_count,
            "hourly": dict(self._hourly_counts),
        }

    def save_state(self, path: str):
        """持久化状态到文件"""
        data = self.get_stats()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2))
