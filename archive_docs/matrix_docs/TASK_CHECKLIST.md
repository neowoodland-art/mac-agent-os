# MC 系统改造任务清单

> 开始: 2026-06-14 | 状态: 进行中
> 目标: 连夜完成全链路改造

---

## 第一阶段: CLI 命令统一 (1-2天) ← 现在开始

### 1.1 清理归档遗留脚本
- [ ] 建 `scripts/archive/` 目录
- [ ] 识别可归档脚本 (测试/调试/不再使用的)
- [ ] 移动归档, 保留核心 15 个脚本
- [ ] 建 `LEGACY_INDEX.md` 说明归档内容

### 1.2 规范 mc 命令入口
- [ ] 检查现有 `mc` 入口 (scripts/mc/ 目录)
- [ ] 包装 `mc collect` (调 collect_batch_runner)
- [ ] 包装 `mc login` (调 login_identity)
- [ ] 包装 `mc sms` (调 sms API)
- [ ] 包装 `mc status` (调 matrix_mgmt)
- [ ] 所有命令支持 `--json` 输出

### 1.3 mc status --json 完善
- [ ] 返回所有账号状态 + 采集时间 + 各平台信息
- [ ] 供 Dashboard 直接消费

---

## 第二阶段: 平台插件化 (3-5天)

### 2.1 建插件框架
- [ ] 建 `platforms/` 根目录
- [ ] 实现 `base.py` 基类 (BasePlatform)
- [ ] 实现插件自动发现 (`__init__.py`)
- [ ] mc 自动加载已注册插件

### 2.2 抖音插件
- [ ] 创建 `platforms/douyin/`
- [ ] 迁移采集逻辑 (现 collect_batch_runner 中的抖音部分)
- [ ] 迁移养号逻辑 (现 nurture_blueprint)
- [ ] 创建 SKILL.md

### 2.3 小红书插件
- [ ] 创建 `platforms/xiaohongshu/`
- [ ] 迁移采集逻辑
- [ ] 修复"我"按钮点击问题
- [ ] 创建 SKILL.md

---

## 第三阶段: 接入开源生态 (1周)

### 3.1 发布功能集成
- [ ] 集成 social-auto-upload 的 douyin_uploader
- [ ] 集成 social-auto-upload 的 xiaohongshu_uploader
- [ ] 包装为 `mc douyin publish` / `mc xhs publish`

### 3.2 搜索互动集成
- [ ] 集成 xiaohongshu-mcp
- [ ] 包装为 `mc xhs search` / `mc xhs interact`

### 3.3 反检测升级
- [ ] 引入高斯抖动 (dy-cli 策略)
- [ ] 引入指数退避

---

## 第四阶段: 联邦多机 + 持续扩展

### 4.1 guardd 改造 (已完成 ✅)
- [x] guardd.py: 心跳数据改写到 agent-local/runtime/guardd/
- [x] 注释掉 _git_sync() 调用, 不再提交 Gitee
- [x] .gitignore: 加入 04_memory/cross_machine/data/
- [x] git rm --cached: 清除 78 个历史心跳文件
- [x] Dashboard guardd 插件: 新增读本机 guardd 状态
- [x] 兼容旧 cross_machine/data/ 数据

### 4.2 Tailscale + mc remote (已完成 ✅)
- [x] app.py: 新增 /api/machine/status 端点 (本机完整状态)
- [x] app.py: 新增 /api/machine/exec 端点 (远程执行 mc 命令)
- [x] mc CLI: 新增 remote 子命令 (list/ping/status/exec)
- [x] 支持 HTTP API 和 SSH 双通道通信
- [x] 代理绕过: requests 库绕过 SOCKS5 代理
- [x] 机器注册表: agent-local/runtime/machines.json
- [x] 文档 FRAMEWORK_V1.md 已更新
- [ ] 安装 Tailscale: `brew install tailscale && tailscale up`

### 4.3 Dashboard 合并
- [ ] 把 matrix_mgmt.html 功能迁移到 index.html
- [ ] 统一侧边栏导航
- [ ] 去重账号列表

### 4.4 历史版本化
- [ ] 每次采集存历史快照
- [ ] Dashboard 加趋势图表
