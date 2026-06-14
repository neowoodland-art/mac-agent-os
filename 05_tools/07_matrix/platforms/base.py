"""MC 平台插件基类"""

from typing import Optional


class BasePlatform:
    """平台插件基类
    
    所有平台插件继承此类, 实现标准接口。
    未实现的接口返回 {"status": "error", "message": "暂不支持"}。
    """
    
    name: str = ""             # 平台标识: 'douyin'
    display_name: str = ""     # 显示名: '抖音'
    version: str = "1.0.0"
    description: str = ""
    
    # ── 登录 ──
    def login(self, account_name: str, headless: bool = False) -> dict:
        return {"status": "error", "message": "暂不支持"}
    
    def logout(self, account_name: str) -> dict:
        return {"status": "error", "message": "暂不支持"}
    
    def status(self, account_name: str) -> dict:
        return {"status": "error", "message": "暂不支持"}
    
    # ── 采集 ──
    def collect(self, account_name: str) -> dict:
        return {"status": "error", "message": "暂不支持"}
    
    # ── 发布 ──
    def publish(self, account_name: str, file_path: str = "",
                title: str = "", desc: str = "") -> dict:
        return {"status": "error", "message": "暂不支持"}
    
    # ── 养号 ──
    def nurture(self, account_name: str, blueprint: str = "daily") -> dict:
        return {"status": "error", "message": "暂不支持"}
    
    # ── 互动 ──
    def interact(self, account_name: str, action: str = "like",
                 target: str = "") -> dict:
        return {"status": "error", "message": "暂不支持"}
    
    # ── 搜索 ──
    def search(self, keyword: str, limit: int = 10) -> dict:
        return {"status": "error", "message": "暂不支持"}


def not_implemented(msg="暂不支持"):
    """返回标准未实现响应"""
    return {"status": "error", "message": msg}
