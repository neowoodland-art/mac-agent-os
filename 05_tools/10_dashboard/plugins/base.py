# plugins/base.py
# Dashboard 数据源插件基类
# 版本: 1.0.0 | 更新: 2026-05-16

from typing import Optional


class DashboardPlugin:
    """数据源插件基类

    每个模块实现此基类, 注册到 Dashboard 作为数据源。
    每个插件对应一个独立的数据源 (AVE / Matrix / guardd 等)。
    """

    # ── 插件元信息 ──────────────────────────────────────────
    name: str = ""          # 唯一标识 (如 "ave", "matrix", "guardd")
    label: str = ""         # 中文展示名 (如 "视频工厂", "矩阵养号", "系统状态")
    order: int = 99         # 展示排序 (值越小越靠前)
    description: str = ""   # 简要描述

    # ── 数据源 API ──────────────────────────────────────────

    def is_available(self) -> bool:
        """检查数据源是否可用 (DB 文件存在等)"""
        raise NotImplementedError

    def get_summary(self) -> dict:
        """总览统计"""
        raise NotImplementedError

    def get_productions(self, limit: int = 50, offset: int = 0,
                         strategy: Optional[str] = None,
                         status: Optional[str] = None) -> list:
        """生产/任务列表"""
        raise NotImplementedError

    def get_production_detail(self, production_id: int) -> Optional[dict]:
        """单条详情"""
        raise NotImplementedError

    def get_cost_breakdown(self) -> list:
        """费用分析"""
        raise NotImplementedError

    # ── 可选覆写 ────────────────────────────────────────────

    def get_sidebar_links(self) -> list[dict]:
        """侧边栏快速链接 (示例: [{"label": "口播策略", "url": "#"}])"""
        return []

    def health_check(self) -> bool:
        """健康检查"""
        return self.is_available()
