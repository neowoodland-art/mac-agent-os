"""
短信验证码 — 抽象接口

所有短信接收方式继承 SMSHandler 基类：
  - ManualSMSHandler: 手动输入（当前默认）
  - AliyunSMSHandler: 阿里云短信转发（预留）
  - TelegramSMSHandler: Telegram bot 推送（预留）
"""
import asyncio
from abc import ABC, abstractmethod


class SMSHandler(ABC):
    """短信验证码处理器抽象基类"""

    @abstractmethod
    async def wait(self, platform: str = "", timeout: int = 120) -> str:
        """等待并返回验证码

        Args:
            platform: 平台名称（用于提示）
            timeout: 超时时间(秒)

        Returns:
            验证码字符串
        """
        ...

    @abstractmethod
    async def cancel(self):
        """取消等待"""
        ...


class ManualSMSHandler(SMSHandler):
    """手动输入验证码（当前默认实现）"""

    async def wait(self, platform: str = "", timeout: int = 120) -> str:
        print(f"\n📱 需要短信验证码 ({platform})")
        print(f"   请查看手机并将验证码输入到终端")
        print(f"   超时: {timeout}秒")

        # 通过信号文件交互（同 login_identity 模式）
        signal_file = f"/tmp/sms_code_{id(self)}.signal"
        try:
            for _ in range(timeout // 2):
                await asyncio.sleep(2)
                if not signal_file:
                    continue
                # 等待用户写入信号文件
                try:
                    with open(signal_file) as f:
                        code = f.read().strip()
                    if code:
                        return code
                except:
                    pass
        except asyncio.CancelledError:
            pass
        return ""

    async def cancel(self):
        """取消等待"""
        print("  ⏹ 短信等待已取消")
