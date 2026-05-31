# AgentOS Matrix 反检测技术方案 v1.0.0

> 最后更新：2026-05-01
> 基于旧版完整手册 + 当前系统现状分析

## 一、当前系统缺失的反检测措施

| 层级 | 缺失项 | 风险 | 旧版实施方案 |
|------|--------|------|-------------|
| **浏览器层** | CDP调试标记 (`--remote-debugging-port`) | 🔴 高 | 已修复：改 Playwright 原生启动 |
| **浏览器层** | `navigator.webdriver` 未覆写 | 🔴 高 | CDP注入 `Object.defineProperty(navigator, 'webdriver', {get:()=>false})` |
| **浏览器层** | `navigator.platform` 与 UA 不一致 | 🟠 中 | 覆写为 `Linux armv8l` (Android) 或 `iPad` |
| **浏览器层** | `navigator.standalone` 未覆写 | 🟠 中 | 强制返回 `false` |
| **浏览器层** | 触摸事件模拟 | 🟠 中 | `Emulation.setTouchEmulationOverride` |
| **行为层** | 无随机动作延迟 | 🔴 高 | `action_delay: [200, 5000]ms` 随机延迟 |
| **行为层** | 无行为画像配置 | 🟠 中 | 每小时点赞上限、评论上限、每日总量 |
| **行为层** | 无观看时长随机化 | 🟠 中 | `view_duration: [5000, 60000]ms` |
| **行为层** | 无打字速度模拟 | 🟠 中 | `typing_speed: [50, 200]ms/char` |
| **网络层** | 无独立IP代理 | 🔴 高 | 静态住宅IP + socks5 代理 |
| **网络层** | 无账号熔断机制 | 🟠 中 | 连续失败3次自动冷却30分钟 |
| **DOM层** | App跳转拦截未完整 | 🟠 中 | 已实现 Fetch 拦截 |
| **DOM层** | 弹窗清理选择器不全 | 🟠 中 | 需要扩展覆盖更多弹窗类型 |
| **操作层** | 搜索后跳转到 `so.douyin.com` | 🟠 中 | 已修复：用首页搜索栏 |

## 二、浏览器启动配置（已修复）

```python
# ✅ 正确：不使用 --remote-debugging-port
# ✅ 正确：在 launch_persistent_context 中设置平板参数
ctx = await pw.chromium.launch_persistent_context(
    user_data_dir=profile,
    channel="chrome",
    headless=False,
    viewport={"width": 702, "height": 783},
    device_scale_factor=2,
    is_mobile=True,
    has_touch=True,
    user_agent="Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X)...",
    locale="zh-CN",
    args=["--no-first-run", "--no-default-browser-check"],
)
```

## 三、需要新增的反检测措施

### 3.1 浏览器指纹覆写

```python
async def apply_fingerprint_protection(page):
    """覆写浏览器指纹特征"""
    await page.evaluate("""() => {
        // 隐藏自动化标记
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
        
        // 平台一致性
        Object.defineProperty(navigator, 'platform', { get: () => 'iPad' });
        
        // 隐藏PWA能力
        Object.defineProperty(navigator, 'standalone', { get: () => false });
        
        // 修改插件检测
        Object.defineProperty(navigator, 'plugins', { 
            get: () => [1, 2, 3, 4, 5] 
        });
        
        // 修改语言
        Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh'] });
    }""")
```

### 3.2 拟人化行为参数

```python
BEHAVIOR_PROFILE = {
    "douyin_01": {
        "action_delay": [0.5, 3.0],       # 动作间隔秒
        "view_duration": [5, 60],          # 浏览停留秒
        "typing_speed": [50, 200],         # 打字 ms/字符
        "max_likes_per_hour": 15,
        "max_comments_per_hour": 3,
        "max_collects_per_hour": 5,
        "active_hours": [8, 23],
        "max_daily_actions": 150,
    }
}
```

### 3.3 账号熔断器

```python
class CircuitBreaker:
    def __init__(self, account_id):
        self.failures = 0
        self.max_failures = 3
        self.cooldown = 1800  # 30分钟
```

### 3.4 IP代理配置

需要为每个账号配置独立静态住宅 IP（当前未配置）。

## 四、实施优先级

| 优先级 | 措施 | 预估工时 |
|--------|------|---------|
| P0 | 浏览器指纹覆写 (webdriver/platform/standalone) | 30分钟 |
| P0 | 随机动作延迟 (action_delay) | 30分钟 |
| P1 | 行为画像配置 (每小时上限/每日上限) | 30分钟 |
| P1 | 弹窗清理扩展 | 15分钟 |
| P1 | 账号熔断器 | 30分钟 |
| P2 | IP代理接入 | 需要外部采购 |
| P2 | 多浏览器内核轮换 | 后续阶段 |

## 五、与旧版对比总结

旧版完整方案包含：隐身容器 (Colima+Docker) → 反检测浏览器 (Camoufox/Patchright) → 移动端伪装 → 拟人化行为 → IP代理 → 熔断机制

当前系统只实现了基础的浏览器控制和页面交互，**反检测层几乎全部缺失**。
需要在后续迭代中逐步补齐。
