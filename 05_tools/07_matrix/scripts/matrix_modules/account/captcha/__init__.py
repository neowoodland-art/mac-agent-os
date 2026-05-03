"""
验证码处理（接口预留）

与 sms/ 类似，captcha 提供验证码（图形/滑块）的抽象接口。
当前默认实现为 ManualCaptchaHandler（手动处理）。
"""

from .base import CaptchaHandler, ManualCaptchaHandler

__all__ = ["CaptchaHandler", "ManualCaptchaHandler"]
