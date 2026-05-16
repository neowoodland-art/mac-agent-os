# plugins/ave.py
# AVE 视频工厂数据源插件
# 版本: 1.0.0 | 更新: 2026-05-16

import sys
from pathlib import Path
from typing import Optional

# ── 添加 AVE scripts 目录到 sys.path ──────────────────────
# 10_dashboard/plugins/ave.py 需要 import AVE 的 lib.dashboard
# 路径: 10_dashboard/ → ../09_ave/scripts/
_AVE_SCRIPTS = Path(__file__).resolve().parents[2] / "09_ave" / "scripts"
if str(_AVE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_AVE_SCRIPTS))

from plugins.base import DashboardPlugin
from lib.dashboard import (
    init_db, get_summary, get_productions,
    get_production_detail, get_cost_breakdown,
)


class AVEDashboardPlugin(DashboardPlugin):
    name = "ave"
    label = "视频工厂"
    order = 1
    description = "AVE 视频生产流水线：口播 / 卡点 / 数字人 / 角色叙事"

    def __init__(self):
        init_db()  # 确保 DB schema 存在

    def is_available(self) -> bool:
        from lib.dashboard import DB_PATH
        return DB_PATH.exists()

    def get_summary(self) -> dict:
        return get_summary()

    def get_productions(self, limit: int = 50, offset: int = 0,
                         strategy: Optional[str] = None,
                         status: Optional[str] = None) -> list:
        return get_productions(limit=limit, offset=offset,
                                strategy=strategy, status=status)

    def get_production_detail(self, production_id: int) -> Optional[dict]:
        return get_production_detail(production_id)

    def get_cost_breakdown(self) -> list:
        return get_cost_breakdown()

    def get_sidebar_links(self) -> list[dict]:
        return [
            {"label": "口播策略", "url": "/#/productions?strategy=口播"},
            {"label": "卡点策略", "url": "/#/productions?strategy=卡点"},
            {"label": "数字人策略", "url": "/#/productions?strategy=数字人"},
            {"label": "角色叙事", "url": "/#/productions?strategy=故事"},
            {"label": "资产浏览器", "url": "/#/assets"},
        ]
