"""
browser_helpers.py — 采集系统的浏览器辅助函数

调用方式：通过 agent-browser skill 或 Playwright 打开 Chrome 页面提取数据。
采集系统绝不使用 Camoufox，只走真实 Chrome。
"""
import asyncio, json, logging

logger = logging.getLogger("dashboard.collect.browser")


async def page_evaluate(url: str, js_code: str) -> dict:
    """
    通过 agent-browser 在 Chrome 中打开 URL，执行 JS 提取数据。

    使用 Playwright 连接真实 Chrome（通过 CDP 或扩展桥接）。
    这是一个兜底降级方案，速度比 OpenCLI 慢但不需要额外依赖。
    """
    # TODO: Phase 2 实现真正的浏览器交互
    # 当前 placeholder，Phase 1 先用 OpenCLI
    logger.warning(f"browser_helpers.page_evaluate 尚未实现（Phase 2），跳过: {url}")
    return {}
