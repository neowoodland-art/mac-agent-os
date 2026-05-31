"""
ui_layout.py — 抖音评论区 UI 布局参数 (v1.0.0)

设计原则（2026-05-09 基于真人操作反馈）：
  - 不硬编码绝对坐标
  - 所有坐标相对于浏览器窗口右边缘、底边缘计算
  - 布局参数可配置（支持 per-account 覆盖）
  - 分为：DOM检测优先 → 坐标落位保底 → 状态验证确认

抖音评论区布局（KeyX 打开后）：
  ┌──────────────────────────────────────┐
  │ 评论面板 (固定宽度 ~500-600px)        │
  │                                      │
  │  评论列表区域                          │
  │                                      │
  │ ┌──────────────────┬──┬──┬──────┐     │
  │ │ 输入框区域         │😊│@│ 发送 │     │
  │ │ 留下你的精彩评论吧   │  │  │      │     │
  │ └──────────────────┴──┴──┴──────┘     │
  └──────────────────────────────────────┘

关键：
  - 输入框在评论面板底部靠左
  - Emoji/ Mention/ Send 按钮在右侧
  - 输入框宽度 = 评论面板宽度 - 右侧按钮区(~130px)
  - 点击位置应落在输入框中间偏左区域
"""

import json
from pathlib import Path
from typing import Dict, Optional, Tuple

__version__ = "1.0.0"


# ── 默认布局参数（基于 702×783 窗口测量） ─────────────────────

DEFAULT_LAYOUT = {
    # 评论面板布局（相对于窗口左边缘）
    "comment_panel": {
        "width_ratio": 0.85,           # 面板占窗口宽度的比例
        "left_offset": 0,              # 面板距离左边缘（像素固定值）
    },

    # 输入框位置（相对于窗口右边缘，因为按钮在右侧）
    "input_box": {
        # 从右边缘往左偏移量（校准值 2026-05-10）
        "from_right_margin": 223,       # 702-479=223（实测 activeElement 中心）
        # 从上边缘往下偏移量
        "from_top_offset": "auto",      # "auto" = 动态检测，fallback 使用下面固定值
        "from_top_fallback": 687,       # 实测 activeElement Y 中心
        "height": 36,                   # 输入框高度
    },

    # 按钮区域（从右边缘往左）
    "buttons": {
        "send_width": 60,               # 发送按钮宽度
        "icon_width": 30,               # emoji/@ 图标宽度
        "button_count": 3,              # 按钮数量 (emoji + @ + 发送)
    },

    # 发送键
    "send_key": {
        "method": "dom",                # dom/alt_enter。DOM 优先找"发送"按钮
        "alt_enter_fallback": True,
    },

    # 验证码弹窗
    "verify_code": {
        "input_placeholder": "验证码",
        "confirm_button_texts": ["确认", "提交", "验证"],
    },
}


def get_layout(account_config: Optional[Dict] = None) -> dict:
    """获取 UI 布局参数（支持 per-account 覆盖）

    Args:
        account_config: accounts.yaml 中的账号配置，可包含 ui_layout 覆盖

    Returns:
        合并后的布局参数字典
    """
    layout = dict(DEFAULT_LAYOUT)
    if account_config and "ui_layout" in account_config:
        # 深度合并
        _deep_merge(layout, account_config["ui_layout"])
    return layout


def _deep_merge(base: dict, override: dict):
    """递归合并字典（不覆盖子键未指定的部分）"""
    for key, val in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(val, dict):
            _deep_merge(base[key], val)
        else:
            base[key] = val


def calc_input_position(window_width: int, window_height: int,
                        layout: Optional[Dict] = None) -> Tuple[int, int]:
    """计算评论输入框的目标点击坐标

    Args:
        window_width: 浏览器窗口宽度 (如 702)
        window_height: 浏览器窗口高度 (如 783)

    Returns:
        (x, y) — 基于 viewport 的绝对坐标
    """
    if layout is None:
        layout = DEFAULT_LAYOUT

    ib = layout["input_box"]

    # X坐标：从窗口右边缘往左偏移
    x = window_width - ib["from_right_margin"]

    # Y坐标
    y = ib.get("from_top_fallback", 720)

    return (x, y)


def calc_panel_rect(window_width: int, window_height: int,
                    layout: Optional[Dict] = None) -> Tuple[int, int, int, int]:
    """计算评论面板的包围矩形（用于 debug / 视觉确认）

    Returns:
        (left, top, width, height)
    """
    if layout is None:
        layout = DEFAULT_LAYOUT
    panel = layout["comment_panel"]
    pw = int(window_width * panel["width_ratio"])
    return (panel["left_offset"], 0, pw, window_height)


def format_layout_summary(layout: Optional[Dict] = None) -> str:
    """生成布局参数的摘要文本（用于日志）"""
    if layout is None:
        layout = DEFAULT_LAYOUT
    ib = layout["input_box"]
    btn = layout["buttons"]
    return (
        f"UI布局: "
        f"输入框右边缘偏移={ib['from_right_margin']}px, "
        f"Y坐标兜底={ib['from_top_fallback']}px, "
        f"按钮数={btn['button_count']}, "
        f"发送方式={layout['send_key']['method']}"
    )
