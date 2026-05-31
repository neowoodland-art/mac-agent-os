# Matrix 养号系统 — 账号登录管理标准化 SOP

> **最后更新**：2026-05-01 15:35  
> **版本**：v1.0.0  
> **适用场景**：所有抖音账号的登录状态检查、重新登录、登录验证、账号切换  
> **核心原则**：每一步可执行、可复现、可验证

---

## 目录

1. [前置环境检查](#1-前置环境检查)
2. [账号登录状态查看](#2-账号登录状态查看)
3. [Cookie 过期账号重登录流程](#3-cookie-过期账号重登录流程)
4. [从未登录账号首次登录流程](#4-从未登录账号首次登录流程)
5. [Camoufox 账号登录流程](#5-camoufox-账号登录流程)
6. [登录验证标准流程](#6-登录验证标准流程)
7. [账号切换标准流程](#7-账号切换标准流程)
8. [故障排查表](#8-故障排查表)

---

## 1. 前置环境检查

**每次做任何操作前，先执行以下检查。** 只有全部通过才继续。

### 1.1 Python 环境

```bash
# 确认 python 可用
/Users/chengzige/.workbuddy/binaries/python/envs/agent-os/bin/python3 --version

# 确认 patchright 安装（核心依赖，缺少则所有操作不可用）
/Users/chengzige/.workbuddy/binaries/python/envs/agent-os/bin/python3 -c "from patchright import __version__; print('patchright', __version__)"
```

**预期输出**：`patchright X.Y.Z`

### 1.2 Chrome 浏览器

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version
```

**预期输出**：`Google Chrome X.Y.Z`  
**当前版本**（2026-04-30）：Google Chrome 147.0.7727.138

### 1.3 账号配置文件完整性

```bash
cat ~/workbuddy-agent-os/agent-local/tools/matrix/config/accounts.yaml
```

确认：
- 所有账号配置的 `enabled` 字段与实际需求一致
- 每个账号的 `profile_dir` 字段正确
- 每个账号的 `port` 端口不冲突（Chrome: 9222-9225 / Camoufox: 9301-9302）

### 1.4 Profile 目录存在性

```bash
ls -d ~/workbuddy-agent-os/agent-local/tools/matrix/profiles/*/
```

**预期**：至少 `account_01`、`douyin_02`、`camoufox_01`、`camoufox_02` 存在。

### 1.5 工具脚本路径

```bash
TOOL=~/workbuddy-agent-os/agent-sync/05_tools/07_matrix
ls $TOOL/scripts/switch_account.py
ls $TOOL/scripts/task_engine.py
ls $TOOL/blueprints/douyin_browse_v2.json
```

**预期**：文件均存在。

---

## 2. 账号登录状态查看

### 2.1 查看 DB 缓存状态

```bash
cd ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix
/Users/chengzige/.workbuddy/binaries/python/envs/agent-os/bin/python3 scripts/switch_account.py --status
```

输出解读：

| DB 状态 | 含义 | 下一步 |
|---------|------|--------|
| `active` | 上次登录已验证有效 | → 执行 [2.2](#22-实时登录验证) 确认实际有效 |
| `cookie_expired` | Cookie 已过期 | → 跳转 [3. Cookie 过期重登录](#3-cookie-过期账号重登录流程) |
| `needs_login` | 该账号从未成功登录 | → 跳转 [4. 首次登录](#4-从未登录账号首次登录流程) |
| `inactive` | 账号已禁用 | 跳过，除非手动启用 |

### 2.2 实时登录验证

DB 状态只是缓存，**必须实时验证**。对每个要使用的账号执行：

```bash
# 1. 启动浏览器（如果未运行）
TOOL=~/workbuddy-agent-os/agent-sync/05_tools/07_matrix
python $TOOL/scripts/switch_account.py --method profile --target douyin_01 --port 9222
```

**这一步会**：
1. 关闭端口上的旧 Chrome
2. 启动新 Chrome（指定 Profile）
3. 注入浏览器指纹
4. 自动导航到 `douyin.com`
5. 检查 `[data-e2e="user-avatar"]` 是否存在
6. 更新 DB 状态

**关键输出**：
```
[4/4] 验证登录状态...
  ✅ 已登录（检测到头像）
```
或
```
  ⚠️ 未登录，需要手动登录或 Cookie 注入
```

---

## 3. Cookie 过期账号重登录流程

**适用账号**：`douyin_01`（当前状态：cookie_expired）  
**适用账号**：任何显示 `cookie_expired` 的 Chrome 账号

### 3.1 启动浏览器

```bash
TOOL=~/workbuddy-agent-os/agent-sync/05_tools/07_matrix

# 关闭端口残留进程
kill -9 $(lsof -ti :9222) 2>/dev/null

# 以手动登录模式启动 Chrome（不关闭窗口）
python $TOOL/scripts/launch_chrome.sh douyin_01 9222
```

### 3.2 手动登录

浏览器窗口打开后：

1. **不要关闭窗口**
2. 导航到 `https://www.douyin.com/`
3. 用手机扫码或验证码登录
4. 等待登录成功（首页显示个人头像）

### 3.3 验证并导出 Cookie

**不要关闭浏览器**，在新终端执行：

```bash
TOOL=~/workbuddy-agent-os/agent-sync/05_tools/07_matrix

# 验证登录
python $TOOL/scripts/switch_account.py --status

# 导出 Cookie
python $TOOL/scripts/switch_account.py --export-cookies --target douyin_01 --port 9222
```

**预期输出**：
```
✅ 导出 10+ 个 Cookie → ~/.../data/cookies/douyin_01_cookies.json
```

### 3.4 更新 DB 状态

导出 Cookie 后，手动确认 DB 已更新为 `active`：

```bash
python $TOOL/scripts/switch_account.py --status | grep douyin_01
```

**预期**：`DB状态: active`

### 3.5 留窗验证 5 分钟

浏览器不关闭，5 分钟后刷新 `douyin.com`，确认：
- 头像仍显示
- 页面可正常滚动
- 退出登录不被踢

---

## 4. 从未登录账号首次登录流程

**适用账号**：`douyin_02`（当前状态：needs_login）

### 4.1 启动浏览器

```bash
TOOL=~/workbuddy-agent-os/agent-sync/05_tools/07_matrix

# 关闭端口残留
kill -9 $(lsof -ti :9223) 2>/dev/null

# 启动（指定该账号的 port 和 profile）
python $TOOL/scripts/launch_chrome.sh douyin_02 9223
```

### 4.2 手动登录

1. 浏览器窗口打开后，导航到 `https://www.douyin.com/`
2. 使用账号 `18500003366` 手机验证码登录
3. 注意：**抖音可能要求短信验证**，需要手机验证码

### 4.3 验证并导出 Cookie

同 [3.3](#33-验证并导出-cookie)，将 `douyin_01` 替换为 `douyin_02`，`9222` 替换为 `9223`。

### 4.4 首次登录特别验证

由于是首次登录（needs_login），额外验证：
1. 确认 Profile 目录已生成登录数据
2. 关闭浏览器，重新用 switch_account.py 启动
3. 确认自动登录成功

```bash
# 关闭浏览器后，重新用标准化流程启动
python $TOOL/scripts/switch_account.py --method profile --target douyin_02 --port 9223
```

**预期**：
```
[4/4] 验证登录状态...
  ✅ 已登录（检测到头像）
  ✅ 切换完成: douyin_02
  CDP: http://localhost:9223
  登录: ✅
```

---

## 5. Camoufox 账号登录流程

**适用账号**：`douyin_camo01`、`douyin_camo02`

### 5.1 检查 Camoufox 环境

```bash
# 检查二进制
ls -la ~/Library/Caches/camoufox/Camoufox.app/Contents/MacOS/camoufox

# 检查 Python 包
/Users/chengzige/.workbuddy/binaries/python/envs/agent-os/bin/python3 -c "import camoufox; print(camoufox.__version__)"
```

### 5.2 启动 Camoufox 浏览器

```bash
# 注意：Camoufox 启动方式不同于 Chrome
# 使用 camoufox_manager 或直接运行的 camoufox_server
/Users/chengzige/.workbuddy/binaries/python/envs/agent-os/bin/python3 \
  ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts/camoufox_server.py \
  --account douyin_camo01
```

### 5.3 手动登录

同 [3.2](#32-手动登录)，导航到 `douyin.com` 并登录。

### 5.4 验证

Camoufox 是 Firefox 内核，验证方式：

```bash
# 检查 Cookie 文件是否存在
ls -la ~/workbuddy-agent-os/agent-local/tools/matrix/data/cookies/*camoufox*
```

### 5.5 注意事项

- Camoufox 当前的 DB 状态显示 `active` 但浏览器未运行，这是**缓存数据失准**
- Camoufox 登录后需在浏览器打开状态下验证
- Camoufox 与 Chrome 的 Cookie 不互通

---

## 6. 登录验证标准流程

无论哪种方式登录后，三步验证：

### 6.1 Cookie 验证

```python
# 从 DB 确认状态
python scripts/switch_account.py --status | grep <account_id>
```

### 6.2 功能验证

执行蓝图前 2 步，确认操作正常：

```bash
TOOL=~/workbuddy-agent-os/agent-sync/05_tools/07_matrix

# 只测试 goto_home + wait_watch（不涉及点赞等）
python $TOOL/scripts/task_engine.py \
  --blueprint douyin_browse_v2 \
  --account douyin_01 \
  --steps 2
```

### 6.3 持久性验证

**关键检验**：关闭浏览器后重新启动，确认能自动登录。

```bash
# 关闭浏览器
kill -9 $(lsof -ti :9222) 2>/dev/null
sleep 2

# 重新启动
python $TOOL/scripts/switch_account.py --method profile --target douyin_01 --port 9222
```

---

## 7. 账号切换标准流程

### 7.1 Profile 切换（推荐，稳定）

```bash
# 从 douyin_01 切换到 douyin_02
python $TOOL/scripts/switch_account.py --method profile --target douyin_02 --port 9223
```

**流程**：关闭旧 Chrome → 启动新 Profile → 注入指纹 → 验证登录

### 7.2 Cookie 注入切换（实验性，快速）

```bash
# 前提：Cookie 文件已导出且未过期
python $TOOL/scripts/switch_account.py --method cookie --target douyin_01 --port 9222
```

**注意**：Cookie 切换要求浏览器已运行。如果 Cookie 过期，自动恢复原 Cookie。

---

## 8. 故障排查表

### 8.1 DB 状态与实际情况对应指南

| DB 状态 | 实际可能性 | 操作 |
|---------|-----------|------|
| `active` | ✅ Cookie 有效，浏览器可运行 | 直接使用 |
| `active` | ❌ Cookie 已过期，缓存未更新 | 执行 [2.2 实时验证](#22-实时登录验证) |
| `cookie_expired` | ✅ 确实过期 | 执行 [3. 重登录](#3-cookie-过期账号重登录流程) |
| `needs_login` | ✅ 从未登录过 | 执行 [4. 首次登录](#4-从未登录账号首次登录流程) |
| `needs_login` | ⚠️ 可能已经手动登录过但 DB 未更新 | 执行 [2.2 实时验证](#22-实时登录验证) |
| 端口无进程 | — | 执行 [2.2 实时验证](#22-实时登录验证) （自动启动浏览器） |

### 8.2 常见错误处理

| 错误 | 根因 | 修复 |
|------|------|------|
| `patchright 未安装` | Python venv 缺少包 | `/Users/chengzige/.workbuddy/binaries/python/envs/agent-os/bin/pip install patchright` |
| `DouyinOps.like() got an unexpected keyword argument 'probability'` | like()/collect() API 参数不兼容 | 更新蓝图去掉 probability 参数，或用旧版 API |
| `连接失败 / 端口无响应` | Chrome 未启动或端口错误 | 先检查端口占用、再启动 |
| `视频加载超时` | 网络问题或页面元素变更 | 增加等待时间或检查 douyin.com 是否可访问 |
| `SEARCH_KEYWORD 未替换` | 蓝图模板变量未配置 | 在 accounts.yaml 中为账号配置 search_keywords 字段 |

### 8.3 当前系统状态基线（2026-05-01）

| 账号 | Profile | 端口 | DB 状态 | 浏览器 | 上次活跃 |
|------|---------|------|---------|--------|---------|
| douyin_01 | account_01 | 9222 | cookie_expired | ⏹ 未运行 | 2026-04-30 14:50 |
| douyin_02 | douyin_02 | 9223 | needs_login | ⏹ 未运行 | 2026-04-30 09:02 |
| douyin_camo01 | camoufox_01 | 9301 | active（缓存） | ⏹ 未运行 | None |
| douyin_camo02 | camoufox_02 | 9302 | active（缓存） | ⏹ 未运行 | None |

---

## 附录 A：标准化检查清单

每次操作前后，对照此清单确认：

- [ ] 前置环境检查通过（patchright、Chrome、配置）
- [ ] 账号当前 DB 状态已记录
- [ ] 浏览器进程状态已记录（运行/未运行）
- [ ] 操作前备份了当前状态
- [ ] 每一步的标准命令已执行
- [ ] 操作后状态已重新验证
- [ ] DB 状态已更新到最新
- [ ] 工作日志已记录（`└ 04_memory/logs/`）

---

## 附录 B：可用命令速查

```bash
TOOL=~/workbuddy-agent-os/agent-sync/05_tools/07_matrix

# 查看状态
python $TOOL/scripts/switch_account.py --list        # 列出所有账号
python $TOOL/scripts/switch_account.py --status       # 查看实时状态

# 启动 + 验证
python $TOOL/scripts/switch_account.py --method profile --target douyin_01 --port 9222

# Cookie 管理
python $TOOL/scripts/switch_account.py --export-cookies --target douyin_01 --port 9222
python $TOOL/scripts/switch_account.py --method cookie --target douyin_01 --port 9222

# 执行蓝图
python $TOOL/scripts/task_engine.py --blueprint douyin_browse_v2 --account douyin_01

# 全面测试
python $TOOL/scripts/full_test.py --skip-launch --account-only douyin_01

# 手动启动浏览器
bash $TOOL/scripts/launch_chrome.sh douyin_01 9222
```
