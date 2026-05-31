"""
验证码处理 — 抽象接口

CaptchaHandler 是所有验证码处理器的基类：
  - ManualCaptchaHandler: 手动处理（默认）
  - OCRCaptchaHandler: OCR 自动识别（预留）
  - ThirdPartyCaptchaHandler: 打码平台（预留）
"""
from abc import ABC, abstractmethod


class CaptchaHandler(ABC):
    """验证码处理器抽象基类"""

    @abstractmethod
    async def solve(self, page=None, timeout: int = 60) -> bool:
        """处理验证码

        Args:
            page: 浏览器页面对象（可选，用于截图/交互）
            timeout: 超时时间(秒)

        Returns:
            是否成功解决
        """
        ...


class ManualCaptchaHandler(CaptchaHandler):
    """手动处理验证码（默认实现）"""

    async def solve(self, page=None, timeout: int = 60) -> bool:
        print(f"\n🔐 需要验证码")
        print(f"   请在浏览器中手动完成验证")
        print(f"   超时: {timeout}秒")
        # 等待用户手动处理
        import asyncio
        for _ in range(timeout):
            await asyncio.sleep(1)
            # 检测页面 URL 是否验证通过（简单实现）
            if page:
                url = page.url
                if 'captcha' not in url.lower() and 'verify' not in url.lower():
                    return True
        return False
