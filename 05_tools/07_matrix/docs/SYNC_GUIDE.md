# Matrix 统— 多机同步标准化指南

> **版本**: v1.0.0  
> **最后更新**: 2026-05-01  
> **适用场景**: 本机测试完成后，将修改同步到其他电脑

---

## 1. 同步架构总览

```
主电脑（Redmi-12C）
    │
    ├── agent-sync/  ←────────── 坚果云 / Gitee ──────────→  agent-sync/（其他电脑）
    │   ├── 02_skills/matrix/        代码 + 文档            │
    │   ├── 05_tools/07_matrix/                             │
    │   └── ...                                              │
    │                                                       │
    └── agent-local/  ←────────── 不同步（每机独立） ────→  agent-local/（其他电脑）
        └── tools/matrix/                                    │
            ├── config/accounts.yaml     (手动配置)          │
            ├── profiles/                (手动登录)          │
            ├── data/cookies/            (重新导出)          │
            └── data/matrix.db           (重新初始化)        │
```

### 同步内容清单

| 类别 | 内容 | 同步方式 | 是否同步 |
|------|------|---------|---------|
| **代码脚本** | scripts/*.py, *.sh | Git + 坚果云 | ✅ |
| **蓝图文件** | blueprints/*.json | Git + 坚果云 | ✅ |
| **标准化文档** | docs/*.md | Git + 坚果云 | ✅ |
| **技能定义** | 02_skills/matrix/ | Git + 坚果云 | ✅ |
| **安装脚本** | install.sh | Git + 坚果云 | ✅ |
| **依赖清单** | requirements.txt | Git + 坚果云 | ✅ |
| **配置模板** | config_template/ | Git + 坚果云 | ✅ |
| **local.yaml** | 本机路径配置 | 每机独立生成 | ❌ |
| **accounts.yaml** | 手机号/端口 | 每机手动配置 | ❌ |
| **Chrome Profile** | 浏览器登录数据 | 每机重新登录 | ❌ |
| **Cookie 文件** | data/cookies/ | 每机重新导出 | ❌ |
| **matrix.db** | 执行记录/DB | 每机重新初始化 | ❌ |
| **Python venv** | 安装的包 | 每机重新安装 | ❌ |
| **Playwright Chromium** | 浏览器二进制 | 每机重新安装 | ❌ |
| **Camoufox** | Firefox 浏览器 | 每机重新安装 | ❌ |

---

## 2. 标准化同步流程

### 2.1 在主电脑上提交修改

```bash
# 1. 确认所有修改已保存
cd ~/workbuddy-agent-os/agent-sync

# 2. 查看修改文件
git status
# 预期看到:
#   modified:  02_skills/matrix/SKILL.md
#   modified:  05_tools/07_matrix/scripts/switch_account.py
#   modified:  05_tools/07_matrix/scripts/cdp_connector.py
#   new file:  05_tools/07_matrix/scripts/auth_manager.py
#   modified:  05_tools/07_matrix/docs/FULL_TEST_REPORT.md
#   new file:  05_tools/07_matrix/docs/SYSTEM_ARCHITECTURE.md
#   new file:  05_tools/07_matrix/docs/SYNC_GUIDE.md

# 3. 提交并推送
git add -A
git commit -m "Matrix 系统修复: 原子化登录模块 + 稳定性修复"
git push origin main
```

> **注意**: 坚果云会同步 `agent-sync/` 目录下的文件修改，但建议以 Git 为主要版本控制手段，坚果云仅作为文件快速分发。两台电脑都需要安装坚果云并登录同一账号。

### 2.2 在其他电脑上拉取更新

```bash
# 方式A: 通过 Git（推荐，版本可控）
cd ~/workbuddy-agent-os/agent-sync
git pull origin main

# 方式B: 通过坚果云（自动同步）
# 确保两台电脑登录同一坚果云账号，agent-sync/ 目录会自动同步
```

### 2.3 在新电脑上运行安装脚本

```bash
# 1. 运行一键安装（建立目录骨架 + 安装依赖 + 生成配置）
bash ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/install.sh

# 2. 安装 Camoufox（额外的 Firefox 浏览器）
~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts/install_camoufox.sh
# 或手动:
# pip install camoufox
# python -m camoufox fetch
```

### 2.4 配置本地账号

```bash
# 编辑本机 accounts.yaml（手机号/端口/备注按本机设置）
vim ~/workbuddy-agent-os/agent-local/tools/matrix/config/accounts.yaml

# 必须修改的字段:
# - phone: 本机对应的手机号
# - port: 确保端口不冲突（Chrome: 9222+, Camoufox: 9301+）
```

### 2.5 初始化数据库（可选）

```bash
# 如果新机没有 matrix.db，初始化一个
cd ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix
~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts/init_db.py
```

### 2.6 重新登录各平台

```bash
# 每个账号需要重新手动登录一次
# Chrome 方案:
cd ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix
python scripts/switch_account.py --method profile --target douyin_01 --port 9222
# → 浏览器打开 douyin.com，扫码登录
# → 登录后自动检测 Cookie → 自动导出到 data/cookies/

# Camoufox 方案:
python scripts/yanghao_runner.py --account douyin_camo01 --blueprint douyin_browse_v2 --browser camoufox
```

---

## 3. 本地依赖完整清单

以下是在新电脑上需要重新部署的所有本地依赖：

### 3.1 Python 包

```bash
# 使用 agent-os 的 Python 环境
PY=~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/install.sh 自动处理

# 或手动安装:
pip install -r ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/requirements.txt
# 包含: patchright, camoufox, PyYAML
```

### 3.2 Playwright 浏览器

```bash
# Chromium（Chrome 方案需要）
python -m patchright install chromium

# 注意: 不需要 firefox（Camoufox 自带 Firefox）
```

### 3.3 Camoufox 浏览器

```bash
# Camoufox 方案需要
pip install camoufox
python -m camoufox fetch
# 下载到: ~/Library/Caches/camoufox/Camoufox.app/
```

### 3.4 本地目录结构

```
agent-local/tools/matrix/
├── config/
│   └── accounts.yaml          # 手动配置（每机不同）
├── data/
│   ├── cookies/               # 登录后自动导出
│   ├── camoufox_pids/         # 运行时自动创建
│   └── matrix.db              # init_db.py 初始化
├── profiles/
│   ├── account_01/            # 登录后自动生成
│   ├── douyin_02/
│   ├── camoufox_01/
│   └── camoufox_02/
├── logs/                      # 运行时日志
└── screenshots/               # 可选
```

---

## 4. 版本对照表

每次修改后，在主电脑上记录修改范围，方便其他电脑核对自己是否拉取了最新代码。

### v2.1.0 (2026-05-01) 修改清单

| 文件 | 修改类型 | 说明 |
|------|---------|------|
| `scripts/auth_manager.py` | **新增** | 原子化登录模块（Cookie 检测/导出/注入） |
| `scripts/switch_account.py` | 修改 | 登录检测改为 auth_manager，自动导出 Cookie |
| `scripts/cdp_connector.py` | 修改 | 添加 os=windows / 中文字体 / 委托 auth_manager |
| `02_skills/matrix/SKILL.md` | 修改 | 更新正确入口、新增原子模块说明 |
| `docs/FULL_TEST_REPORT.md` | 修改 | 新增修复记录、已验证功能 |
| `docs/SYSTEM_ARCHITECTURE.md` | **新增** | 全链路系统架构文档 |
| `docs/ACCOUNT_LOGIN_SOP.md` | **新增** | 账号登录标准化操作流程 |
| `docs/SYNC_GUIDE.md` | **新增** | 多机同步指南（本文） |
| `blueprints/douyin_browse_v3.json` | DB注册 | 已在主电脑注册到 task_blueprints |
| `blueprints/douyin_nurture_v1.json` | DB注册 | 同上 |
| `profiles/douyin_01/` | 删除 | 冗余目录（11MB） |

**新机注意事项**:
- DB 注册的蓝图（v3/nurture）需在新机重新运行 `init_db.py` 或在首次使用时自动注册
- 删除冗余目录是主电脑操作，新机没有这个目录，无需处理

---

## 5. 常见问题

### Q: 为什么不能直接复制 Chrome Profile？
Chrome Profile 包含设备绑定的加密数据（Cookie 用本机密钥加密），复制到其他电脑会失效。必须在新机重新扫码登录。

### Q: 为什么 accounts.yaml 不能同步？
每个账号绑定的手机号是固定的，但不同电脑上 Chrome Profile 目录路径和端口分配可能不同（例如一台电脑 9222 已占用，需要用 9224）。

### Q: 主电脑上的修改如何确保不丢失？
```bash
# 养成好习惯：每次修改后
cd ~/workbuddy-agent-os/agent-sync
git add -A
git commit -m "描述修改内容"
git push origin main
```

### Q: 新电脑需要安装什么额外软件？
- 坚果云（同步 agent-sync/ 文件）
- Git（拉取代码）
- Chrome 浏览器（养号工具使用）
- agent-os 的 Python 环境（install.sh 自动处理）

---

## 6. 快速检查清单

新机部署完成后，逐项确认：

- [ ] Git pull 或坚果云同步完成
- [ ] install.sh 运行成功
- [ ] Camoufox 安装完成（如需要）
- [ ] accounts.yaml 已配置本机账号
- [ ] matrix.db 已初始化
- [ ] Chrome Profile 已重新登录
- [ ] Cookie 已自动导出
- [ ] `python scripts/switch_account.py --status` 显示 active
- [ ] `python scripts/auth_manager.py 9222` 显示 sessionid ✅
