# 阶段A 完成总结 — CDP 直连 + 原子操作 + 账号切换

> **完成日期**: 2026-04-27 | **阶段**: A | **状态**: ✅ 全部完成

---

## 一、阶段A 目标回顾

| 目标 | 状态 | 说明 |
|------|------|------|
| CDP 直连本机 Chrome | ✅ | 通过 Patchright `connect_over_cdp` 连接 |
| 原子操作库 V2 | ✅ | 18 个原子操作，基于 `data-e2e` 选择器 |
| 蓝图执行引擎 | ✅ | `task_engine.py` 支持 JSON 蓝图顺序执行 |
| 定时调度器 | ✅ | `task_scheduler.py` 支持 cron 表达式 |
| 账号切换器 | ✅ | `switch_account.py` 双方案（Profile/Cookie） |
| 指纹注入 | ✅ | 视口+时区+语言+WebGL+webdriver+plugins+App拦截 |
| 双账号并行 | ✅ | 端口 9222 + 9223 同时运行 |

---

## 二、核心文件清单

| 文件 | 路径 | 用途 |
|------|------|------|
| 原子操作库 | `scripts/douyin_ops.py` | 18 个原子操作（基于 data-e2e） |
| CDP 连接器 | `scripts/cdp_connector.py` | CDP 连接管理 |
| 蓝图引擎 | `scripts/task_engine.py` | 读取蓝图→顺序执行 |
| 定时调度 | `scripts/task_scheduler.py` | cron 调度 |
| 蓝图入库 | `scripts/seed_db.py` | 初始化蓝图到数据库 |
| 账号切换器 | `scripts/switch_account.py` | Profile切换+指纹注入+Cookie注入 |
| 账号配置 | `config/accounts.yaml` | 4 个账号 + 全局视口 |
| 数据库 | `data/matrix.db` | 6 表 + 4 蓝图 + 4 账号 |
| 选择器手册 | `docs/DOUYIN_SELECTORS.md` | data-e2e 选择器对照 |
| 完整方案 | `docs/DOUYIN_FULL_PLAN.md` | V3.1 架构+蓝图+反检测+IP方案 |
| IP 切换指南 | `docs/IP_SWITCH_GUIDE.md` | 免费方案+付费推荐+技术集成 |
| 本总结 | `docs/PHASE_A_SUMMARY.md` | 阶段A 完成归档 |

---

## 三、账号配置详情

| 账号ID | 平台 | 端口 | Profile | 状态 |
|--------|------|------|---------|------|
| douyin_01 | 抖音 | 9222 | account_01 | ✅ 已登录（主号） |
| douyin_02 | 抖音 | 9223 | douyin_02 | ⏹ 待登录（副号） |
| xhs_01 | 小红书 | 9224 | xhs_01 | ⏹ 待注册 |
| zhihu_01 | 知乎 | 9225 | zhihu_01 | ⏹ 待注册 |

### 视口配置（全局默认）

```yaml
viewport:
  width: 702
  height: 783
  mobile: false    # 桌面端模式
```

> 实测来源：ghai 手动调整两个 Chrome 窗口至满意尺寸后，通过 AppleScript 读取确认。

---

## 四、蓝图清单

| 蓝图ID | 名称 | 步骤数 | 状态 |
|--------|------|--------|------|
| `douyin_browse_v2` | 日常浏览V2 | 11 | ✅ active |
| `douyin_search_browse` | 搜索浏览 | 7 | ✅ active |
| `douyin_comment_interact` | 评论互动 | 8 | ✅ active |
| `douyin_browse` | 日常浏览V1 | 8 | ⛔ deprecated |

---

## 五、踩坑记录（重要经验）

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `hash()` 跨进程不一致 | Python `hash()` 随机种子 | 改用 `sum(ord(c))` 确定性哈希 |
| 移动端 UA 覆盖破坏登录 | Android UA 导致 Cookie 校验失败 | 不覆盖 UA，保持浏览器原生 UA |
| 移动端视口破坏登录 | `mobile: True` 改变渲染模式 | `mobile: False`，桌面端模式 |
| 视口过窄(480px) | 初始参数不当 | 实测确认 702x783 为最佳 |
| PyYAML 未安装 | 简易解析器不含 viewport | 更新 `_parse_yaml_simple()` 支持 viewport 块 |
| Profile 目录名错误 | 配置写 douyin_01 实际是 account_01 | 修正 accounts.yaml |

---

## 六、反检测现状

### ✅ 已实现

- Patchright 自动处理 `navigator.webdriver`
- WebGL Vendor/Renderer 注入（NVIDIA GTX 1660 SUPER）
- HeadlessChrome 标记移除
- navigator.plugins/languages 伪装
- App deeplink 拦截（CDP Fetch）
- 时区/语言统一中国
- 真实 Chrome 浏览器（非 Headless）
- 每账号独立 Profile + 端口
- 同账号指纹模板稳定映射

### ⏹ 待实现

- 鼠标轨迹仿真（贝塞尔曲线）
- Canvas/AudioContext 指纹噪声
- 静态住宅 IP 接入
- 活跃时段控制

---

## 七、IP 方案结论

| 方案 | 成本 | 适用场景 |
|------|------|---------|
| 家里 WiFi + 手机热点 | ¥0 | 2-3 账号 |
| 巨量HTTP 静态住宅 | ¥3-6/个/月 | 养号首选 |
| IPFoxy 静态住宅 | ¥5-8/个/月 | 备选 |

> 技术集成：Chrome 启动时 `--proxy-server=http://user:pass@proxy:port`

---

## 八、下一步：阶段B 规划

| 优先级 | 任务 | 说明 |
|--------|------|------|
| P0 | douyin_02 登录并导出 Cookie | 手动登录一次后 export-cookies |
| P1 | 鼠标轨迹仿真 | 贝塞尔曲线 + 加减速 |
| P1 | 语料库填充 | 评论模板/搜索关键词 |
| P2 | 静态住宅 IP 接入 | 购买后集成到 launch_chrome |
| P2 | Cookie 方案B 完善 | 当前骨架可用，需更多测试 |
| P3 | Docker + Camoufox | 多账号容器化部署 |

---

## 九、关键命令速查

```bash
# 切换账号
python scripts/switch_account.py --method profile --target douyin_01 --port 9222

# 双账号并行
# 终端1:
python scripts/switch_account.py --method profile --target douyin_01 --port 9222
# 终端2:
python scripts/switch_account.py --method profile --target douyin_02 --port 9223

# 导出 Cookie
python scripts/switch_account.py --target douyin_01 --export-cookies

# 查看状态
python scripts/switch_account.py --status

# 列出账号
python scripts/switch_account.py --list
```
