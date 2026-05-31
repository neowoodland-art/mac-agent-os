"""
短信验证码处理

使用方式：
  from matrix_modules.account.sms import SMSHandler, ManualSMSHandler, ApiSMSHandler

  # 自动模式（API 轮询）
  handler = ApiSMSHandler()
  code = await handler.wait("抖音", timeout=120)

  # 手动模式
  handler = ManualSMSHandler()
  code = await handler.wait("抖音")
"""

from .base import SMSHandler, ManualSMSHandler
from .api import ApiSMSHandler

__all__ = ["SMSHandler", "ManualSMSHandler", "ApiSMSHandler"]
