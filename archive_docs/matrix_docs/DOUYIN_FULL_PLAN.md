# 抖音 Web 端任务接管 — 完整方案文档

> **版本**: 3.1 | **日期**: 2026-04-27 | **平台**: 抖音网页版
> **前置条件**: Chrome + CDP 端口 9222 + Patchright
> **阶段A状态**: ✅ 完成（原子操作库V2 + 账号切换器 + 指纹注入 + 双账号并行）

---

## 一、架构总览

```
自然语言指令 / 蓝图 JSON
        ↓
    蓝图引擎 (task_engine.py)
        ↓
    原子操作库 (douyin_ops.py)
        ↓
    账号切换器 (switch_account.py)    ← V3 新增
        ├── 方案A: Chrome Profile 切换 + 指纹注入
        └── 方案B: Cookie 注入（实验性）
        ↓
    CDP 连接器 (cdp_connector.py)
        ↓
    Chrome (端口 9222/9223/...) → 抖音网页
        ↓
    代理 IP (静态住宅 IP)             ← V3 新增
```

### 核心设计原则

1. **原子化**：每个操作是最小不可分割单元，含前置检查+执行+后置验证
2. **固定起点**：所有蓝图从推荐页 (`goto_home`) 出发，确保状态一致
3. **选择器优先**：`data-e2e` > XPath > 键盘 > 鼠标坐标
4. **频率安全**：内置操作频率上限（点赞<20/h，评论<5/h）
5. **验证码降级**：评论触发验证码 → 取消 → 记录 → 继续
6. **账号隔离**：每个账号独立 Profile + 独立端口 + 独立 IP（V3 新增）
7. **指纹稳定**：同一账号永远同一指纹模板，不跨进程漂移（V3 新增）

---

## 二、原子操作清单

| 原子操作 | 方法名 | 选择器 | 键盘备选 | 后置验证 |
|---------|--------|--------|---------|---------|
| 回推荐页 | `goto_home()` | `[data-e2e="douyin-navigation"] a:has-text("推荐")` | - | video.duration > 0 |
| 导航到URL | `goto_url(url)` | - | - | URL 变化 |
| 后退 | `go_back()` | - | - | URL 变化 |
| 点赞 | `like()` | `[data-e2e="video-player-digg"]` | Z | data-e2e-state 变化 |
| 收藏 | `collect()` | `[data-e2e="video-player-collect"]` | - | - |
| 关注 | `follow()` | `[data-e2e="feed-follow-icon"]` | F | - |
| 下翻视频 | `next_video()` | `[data-e2e="video-switch-next-arrow"]` | ↓ | modal_id 变化 |
| 上翻视频 | `prev_video()` | `[data-e2e="video-switch-prev-arrow"]` | ↑ | modal_id 变化 |
| 播放/暂停 | `toggle_play()` | - | 空格 | video.paused 变化 |
| 搜索 | `search(keyword)` | `[data-e2e="searchbar-input"]` | - | URL 含 search |
| 点击搜索结果 | `click_search_result(idx)` | `.search-result-card` | - | URL 含 modal_id |
| 打开评论 | `open_comments()` | `[data-e2e="feed-comment-icon"]` | X | comment_list 出现 |
| 关闭评论 | `close_comments()` | - | X | comment_list 消失 |
| 发评论 | `post_comment(text)` | `.public-DraftEditor-content` | Enter | verify_panel? |
| 取消验证码 | `cancel_verify()` | `.uc-ui-verify_sms-verify_button.second` | - | 面板消失 |
| 观看等待 | `wait_watch(secs)` | - | - | 时间到 |

---

## 三、键盘快捷键

| 键 | 功能 | 可靠性 | 建议 |
|----|------|-------|------|
| Z | 点赞 | ❌ 焦点问题 | 用点击选择器 |
| X | 评论 | ✅ 基本可靠 | 推荐 |
| F | 关注/进直播间 | ✅ | 推荐 |
| B | 弹幕开关 | ✅ | |
| 空格 | 播放/暂停 | ⚠️ 需焦点 | 点击视频先 |
| ↑ | 上一个视频 | ⚠️ 需焦点 | 用点击箭头 |
| ↓ | 下一个视频 | ⚠️ 需焦点 | 用点击箭头 |
| Enter | 搜索确认/评论发送 | ✅ | |

---

## 四、蓝图清单

| 蓝图ID | 名称 | 步骤数 | 状态 |
|--------|------|--------|------|
| `douyin_browse_v2` | 日常浏览V2 | 11 | ✅ active |
| `douyin_search_browse` | 搜索浏览 | 7 | ✅ active |
| `douyin_comment_interact` | 评论互动 | 8 | ✅ active |
| `douyin_browse` | 日常浏览V1 | 8 | ⛔ deprecated |

---

## 五、稳定链路设计

### 5.1 固定起点流程

```
所有蓝图 → 第1步 goto_home() → 等视频加载 → 后续操作
```

这确保每次执行从同一状态出发，不依赖上次操作的页面残留状态。

### 5.2 错误恢复策略

| 错误类型 | 恢复动作 |
|---------|---------|
| 元素未找到 | 等待1s重试 → 刷新页面重试 → 放弃当前步骤继续 |
| 验证码弹出 | cancel_verify() → 记录 → 继续 |
| 页面空白/加载超时 | goto_home() 重新开始 |
| CDP 断连 | 报错退出，调度器30分钟后重试 |
| 连续3步失败 | 熔断：暂停当前蓝图，跳到下一个 |

### 5.3 操作频率控制

```python
RATE_LIMITS = {
    "likes_per_hour":    20,
    "comments_per_hour":  5,
    "follows_per_hour":  10,
    "collects_per_hour": 15,
    "searches_per_hour": 10,
}
```

超过频率的操作自动跳过，不报错。

---

## 六、选择器维护策略

### 6.1 三级定位

| 优先级 | 方式 | 覆盖率 | 失败处理 |
|--------|------|--------|---------|
| L1 | `data-e2e` 选择器 | 95% | 降级到 L2 |
| L2 | XPath / class 选择器 | 4% | 降级到 L3 |
| L3 | MLX 视觉定位 | 1% | 人工介入 |

### 6.2 变更检测

每次操作记录 `locator_used`，如果 L1 选择器连续失败 3 次：
1. 自动写入 `ui_changes` 表
2. 标记受影响蓝图状态为 `broken`
3. 通知人工扫描页面更新选择器

---

## 七、账号切换 + 反检测方案

### 7.1 当前两套逻辑

| 方案 | 逻辑 | 优点 | 缺点 |
|------|------|------|------|
| **A: Chrome Profile 切换** | 每个账号独立 `--user-data-dir`，切换 = 重启 Chrome | Cookie 自然持久化，最简单 | 切换慢（需关闭重开Chrome），同时间只能1个账号 |
| **B: Cookie 注入** | 1个浏览器实例，通过 CDP 注入不同 Cookie | 切换快（秒级），可同时多标签 | Cookie 格式复杂，部分平台有额外校验，反检测弱 |

### 7.2 推荐方案：A 为主，B 备用

**现阶段（2-5个账号）**：方案 A 足够
- 每个账号一个 Chrome Profile 目录
- 切换 = 关 Chrome → 重新 `launch_chrome.sh <账号ID> <端口>`
- 间隔 10-30 分钟自然切换

**扩展阶段（5+账号）**：方案 B 补充
- 提取 Cookie → JSON 存储 → 注入到新上下文
- 需要 `cdp_connector.py` 增加 `inject_cookies()` 方法

### 7.3 反检测清单

| 检测维度 | 当前措施 | 下一步 |
|---------|---------|--------|
| **浏览器指纹** | 真实 Chrome（指纹原生） | 阶段B：Camoufox/Patchright 容器 |
| **navigator.webdriver** | Patchright 自动处理 | ✅ 已覆盖 |
| **IP地址** | 同一IP（风险中等） | 静态住宅IP（每账号独立） |
| **行为模式** | 随机延迟+频率控制 | 增加鼠标轨迹仿真 |
| **Cookie/Session** | Chrome Profile 自然持久 | ✅ 已覆盖 |
| **操作时间** | 随机间隔 2-15s | 增加活跃时段控制（8:00-23:00） |
| **账号关联** | 同一设备不同Profile | 独立代理IP + 不同的浏览习惯 |

### 7.4 账号切换操作流程

```
1. 结束当前账号蓝图执行
2. 记录执行日志到 operation_logs
3. 关闭 Chrome（kill进程或关闭窗口）
4. 等待 30-120 秒（模拟人工间隔）
5. 启动新账号 Chrome：
   bash ~/matrix/scripts/launch_chrome.sh <新账号ID> <新端口>
6. 等待 Chrome 就绪
7. 验证 Cookie 是否有效（check_login）
8. 开始新账号蓝图执行
```

### 7.5 下一步实施优先级

| 优先级 | 任务 | 预计时间 | 状态 |
|--------|------|---------|------|
| **P0** | 账号切换脚本 `switch_account.py` | 2h | ✅ 已完成 |
| **P0** | 指纹注入 + 双账号并行验证 | 2h | ✅ 已完成 |
| **P1** | 鼠标轨迹仿真（贝塞尔曲线） | 4h | 待开发 |
| **P1** | 语料库填充（评论/关键词） | 1h | 待开发 |
| **P2** | Cookie 注入方案 B 完善 | 4h | 骨架已有 |
| **P2** | 静态住宅IP接入 | 按服务商 | 待购买 |
| **P3** | 阶段B：Docker + Camoufox | 2-3天 | 待规划 |

---

## 八、账号切换系统（V3 新增）

### 8.1 两种切换方案

| 方案 | 机制 | 切换速度 | 可靠性 | 适用场景 |
|------|------|---------|--------|---------|
| **A: Profile 切换** | 关闭 Chrome → 启动新 Profile → 注入指纹 | ~15秒 | ⭐⭐⭐⭐⭐ | 日常养号 |
| **B: Cookie 注入** | 清除 Cookie → 注入新 Cookie → 刷新验证 | ~5秒 | ⭐⭐⭐ | 快速切换（实验性） |

### 8.2 switch_account.py 用法

```bash
# 列出所有账号
python scripts/switch_account.py --list

# 查看当前状态
python scripts/switch_account.py --status

# 方案A: 切换到 douyin_01
python scripts/switch_account.py --method profile --target douyin_01 --port 9222

# 方案B: Cookie 注入切换
python scripts/switch_account.py --method cookie --target douyin_02 --port 9222

# 导出当前 Cookie（给方案B备用）
python scripts/switch_account.py --target douyin_01 --export-cookies
```

### 8.3 切换流程（方案A）

```
1. 关闭当前 Chrome（SIGTERM → 等待 → SIGKILL）
2. 启动新 Chrome（目标 Profile + CDP 端口 + 代理）
3. 注入浏览器指纹：
   - 视口覆盖（桌面端 702x783，保持 Cookie 兼容）
   - 时区覆盖（Asia/Shanghai）
   - 语言覆盖（zh-CN）
   - WebGL Vendor/Renderer 注入（覆盖 GPU 指纹）
   - navigator.webdriver 隐藏
   - navigator.plugins/languages 伪装
   - App 跳转拦截（CDP Fetch）
4. 验证登录状态
5. 更新数据库
```

### 8.4 指纹模板映射

每个账号 ID 稳定映射到一个指纹模板（同一账号永远同一指纹）：

| 账号 | 指纹模板 | 视口 | 设备 |
|------|---------|------|------|
| douyin_01 | fp_iphone14pro | 393x852 | iPhone 14 Pro |
| douyin_02 | fp_samsung24 | 412x915 | Samsung S24 |
| xhs_01 | fp_iphone15pro | 393x852 | iPhone 15 Pro |
| zhihu_01 | fp_huawei_p60 | 393x873 | Huawei P60 |

> ⚠️ 当前养号场景使用桌面端视口（702x783），移动端视口会破坏 Cookie 登录态。
> 移动端伪装仅在特殊需要时通过 cdp_connector 单独开启。

### 8.5 双账号同时运行

每个账号使用不同的 CDP 端口和 Profile 目录：

```bash
# 终端1: 启动账号1（端口 9222）
python scripts/switch_account.py --method profile --target douyin_01 --port 9222

# 终端2: 启动账号2（端口 9223）
python scripts/switch_account.py --method profile --target douyin_02 --port 9223
```

---

## 九、反检测策略（V3 新增）

### 9.1 当前已实现的反检测

| 维度 | 措施 | 实现方式 | 状态 |
|------|------|---------|------|
| **navigator.webdriver** | 隐藏自动化标记 | init_script `undefined` | ✅ |
| **HeadlessChrome** | 移除 Headless 标记 | init_script | ✅ |
| **WebGL 指纹** | 覆盖 GPU 信息 | init_script | ✅ |
| **App 跳转** | 拦截 deeplink | CDP Fetch | ✅ |
| **时区/语言** | 统一为中国 | CDP Emulation | ✅ |
| **浏览器** | 真实 Chrome | 非 Headless | ✅ |
| **plugins** | 伪装非空 | init_script | ✅ |
| **Patchright** | 自动处理自动化检测 | 框架级 | ✅ |

### 9.2 待实现的反检测

| 维度 | 方案 | 优先级 |
|------|------|--------|
| **鼠标轨迹** | 贝塞尔曲线仿真（避免完美直线） | P1 |
| **输入节奏** | press_sequentially + 随机延迟 | P1（已部分实现） |
| **Canvas 指纹** | 噪声注入 | P2 |
| **AudioContext 指纹** | 噪声注入 | P2 |
| **字体指纹** | 覆盖字体列表 | P3 |
| **IP 地址** | 静态住宅代理 | P1（见 IP 方案） |

### 9.3 鼠标轨迹仿真（下一步）

当前点击是"瞬移"到目标位置，这不符合人类行为。下一步实现：

```python
# 贝塞尔曲线鼠标移动
async def human_move_mouse(page, target_x, target_y, steps=20):
    """模拟人类鼠标移动（贝塞尔曲线 + 加减速）"""
    current = await page.evaluate('() => ({x: window._mx || 0, y: window._my || 0})')
    start_x, start_y = current['x'], current['y']
    
    # 随机控制点（贝塞尔曲线）
    ctrl_x = start_x + (target_x - start_x) * 0.5 + random.uniform(-50, 50)
    ctrl_y = start_y + (target_y - start_y) * 0.5 + random.uniform(-50, 50)
    
    for i in range(steps):
        t = i / steps
        # ease-in-out 加速曲线
        t = t * t * (3 - 2 * t)
        x = (1-t)**2 * start_x + 2*(1-t)*t * ctrl_x + t**2 * target_x
        y = (1-t)**2 * start_y + 2*(1-t)*t * ctrl_y + t**2 * target_y
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.01, 0.03))
```

---

## 十、IP 切换方案（V3 新增）

> 详见 `docs/IP_SWITCH_GUIDE.md`

### 10.1 核心结论

- **养号最佳选择**：静态住宅 IP（固定 IP + 真实住宅 + 无限流量）
- **推荐服务商**：巨量HTTP（¥3-6/个/月）、IPFoxy（¥5-8/个/月）
- **最低成本方案**：家里 WiFi + 手机热点（¥0，2-3 个账号）
- **不推荐**：数据中心 IP（易识别）、免费代理（不稳定）

### 10.2 推荐方案（5-10 个账号）

```
买 2-3 个中国静态住宅 IP → 每个 IP 绑 2-3 个账号
成本：¥30-50/月
```

### 10.3 技术集成

Chrome 启动时注入代理：
```bash
"$CHROME" \
    --proxy-server="http://user:pass@proxy.example.com:8080" \
    --remote-debugging-port="$DEBUG_PORT" \
    --user-data-dir="$PROFILE_DIR"
```

账号配置增加代理字段：
```yaml
accounts:
  - id: douyin_01
    proxy: "http://user:pass@cn-proxy1:8080"
  - id: douyin_02
    proxy: "socks5://user:pass@cn-proxy2:1080"
```
