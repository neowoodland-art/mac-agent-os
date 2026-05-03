"""
短信验证码处理（接口预留）

使用方式：
  from matrix_modules.account.sms import SMSHandler

  handler = SMSHandler()
  code = await handler.wait("抖音", timeout=120)  # 等待短信，最多120秒
  # 当前默认实现是 manual.py（手动输入）
  # 以后可替换为 aliyun.py / telegram.py 等自动方案
"""

from .base import SMSHandler, ManualSMSHandler

__all__ = ["SMSHandler", "ManualSMSHandler"]
