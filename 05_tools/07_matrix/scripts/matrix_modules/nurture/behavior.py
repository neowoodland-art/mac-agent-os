"""
行为模拟参数配置 — 拟人化操作行为

每个身份可以独立配置 behavior 参数，覆盖默认值。
默认配置在 DEFAULT_CONFIG 中定义，用户可在 identities/{name}/config.yaml 中覆盖。
"""
import random
import time
from typing import Optional

# ── 默认行为配置 ──────────────────────────────────────────────

DEFAULT_CONFIG = {
    # 基础延迟
    'base_delay': 1.5,            # 操作间基础间隔(秒)
    'delay_variance': 0.8,        # 随机波动范围

    # 鼠标行为
    'mouse': {
        'speed_range': [0.5, 1.5],    # 鼠标移动速度系数
        'click_delay': [0.08, 0.25],  # 点击前停顿(秒)
    },

    # 滚动行为
    'scroll': {
        'mode': 'human',              # human / random / fast
        'pause_chance': 0.3,          # 滚动中暂停的概率
        'pause_duration': [0.5, 2.0], # 暂停时长范围(秒)
        'distance_range': [200, 700], # 每次滚动距离(px)
    },

    # 操作顺序
    'sequence': {
        'shuffle': True,              # 是否打乱操作顺序
        'repetition_chance': 0.1,     # 重复上一个操作的概率
        'min_gap': 1.5,               # 操作间最小间隔(秒)
        'max_gap': 6.0,               # 操作间最大间隔(秒)
    },

    # 注意力模拟
    'attention': {
        'distraction_chance': 0.05,   # "分心"概率
        'distraction_duration': [2, 6], # 分心持续时长(秒)
        'watch_duration': [4, 12],    # 观看视频时长(秒)
        'linger_after_action': [1, 4], # 操作后的停留(秒)
    },

    # 轮间休息
    'round_break': {
        'min_break': 5,               # 轮间最短休息(秒)
        'max_break': 20,              # 轮间最长休息(秒)
    },

    # ★ 反检测 — 拟人化操作策略（2026-05-04）
    'anti_detection': {
        'card_position_range': [0, 4],    # 点卡片时选第几个（0=第1个）
        'search_result_range': [1, 4],    # 搜索结果点第几个（0=第1个）
        'use_keyboard_like': False,       # 是否用键盘 L 键点赞（预留）
        'use_close_button': False,        # 是否用X按钮返回（预留）
        'scroll_method': 'mouse',         # 切换方式: mouse/keyboard/js
    },

    # 异常处理
    'retry': {
        'max_retries': 2,            # 操作失败最大重试次数
        'retry_delay': [1, 3],       # 重试前等待(秒)
    },
}


class BehaviorConfig:
    """行为配置 — 控制所有操作的拟人化参数"""

    def __init__(self, config: Optional[dict] = None):
        self._cfg = DEFAULT_CONFIG.copy()
        if config:
            self._deep_merge(self._cfg, config)

    def _deep_merge(self, base: dict, override: dict):
        """递归合并配置"""
        for key, val in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(val, dict):
                self._deep_merge(base[key], val)
            else:
                base[key] = val

    # ── 延迟方法 ──────────────────────────────────────────

    def action_delay(self) -> float:
        """两个操作之间的随机延迟"""
        base = self._cfg['base_delay']
        variance = self._cfg['delay_variance']
        return max(0.3, base + random.uniform(-variance, variance))

    def sequence_gap(self) -> float:
        """操作序列之间的间隔"""
        sg = self._cfg['sequence']
        return random.uniform(sg['min_gap'], sg['max_gap'])

    def click_delay(self) -> float:
        """点击前的微停顿"""
        cd = self._cfg['mouse']['click_delay']
        return random.uniform(cd[0], cd[1])

    # ── 滚动方法 ──────────────────────────────────────────

    def scroll_distance(self) -> int:
        """每次滚动的距离"""
        dr = self._cfg['scroll']['distance_range']
        return random.randint(dr[0], dr[1])

    def should_pause_scroll(self) -> bool:
        """滚动中是否应该暂停"""
        return random.random() < self._cfg['scroll']['pause_chance']

    def scroll_pause(self) -> float:
        """滚动暂停时长"""
        pd = self._cfg['scroll']['pause_duration']
        return random.uniform(pd[0], pd[1])

    # ── 注意力方法 ────────────────────────────────────────

    def watch_duration(self) -> float:
        """观看一个视频的时长"""
        wd = self._cfg['attention']['watch_duration']
        return random.uniform(wd[0], wd[1])

    def should_distract(self) -> bool:
        """是否应该"分心"（模拟走神）"""
        return random.random() < self._cfg['attention']['distraction_chance']

    def distraction_duration(self) -> float:
        """分心持续时长"""
        dd = self._cfg['attention']['distraction_duration']
        return random.uniform(dd[0], dd[1])

    def linger_after_action(self) -> float:
        """操作后的停留"""
        la = self._cfg['attention']['linger_after_action']

    # ── 反检测方法 ────────────────────────────────────────

    def card_position(self) -> int:
        """随机选视频卡片位置（避免每次都点第1个）"""
        cr = self._cfg['anti_detection']['card_position_range']
        return random.randint(cr[0], cr[1])

    def search_result_position(self) -> int:
        """随机选搜索结果位置（避免每次都点第1个）"""
        sr = self._cfg['anti_detection']['search_result_range']
        return random.randint(sr[0], sr[1])
        return random.uniform(la[0], la[1])

    # ── 轮间休息 ──────────────────────────────────────────

    def round_break(self) -> float:
        """轮间休息时长"""
        rb = self._cfg['round_break']
        return random.uniform(rb['min_break'], rb['max_break'])

    # ── 操作顺序 ──────────────────────────────────────────

    def should_shuffle(self) -> bool:
        """是否打乱操作顺序"""
        return self._cfg['sequence']['shuffle']

    def should_repeat(self) -> bool:
        """是否重复上一个操作"""
        return random.random() < self._cfg['sequence']['repetition_chance']

    # ── 重试 ──────────────────────────────────────────────

    def retry_delay(self) -> float:
        """重试前等待"""
        rd = self._cfg['retry']['retry_delay']
        return random.uniform(rd[0], rd[1])

    @property
    def max_retries(self) -> int:
        return self._cfg['retry']['max_retries']

    # ── 工具方法 ──────────────────────────────────────────

    def sleep(self, seconds: float):
        """带拟人化的 sleep（加入微抖动）"""
        jitter = random.uniform(-0.05, 0.05)
        time.sleep(max(0, seconds + jitter))
