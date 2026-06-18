# AgentOS Agent Initialization Guide

> **Version**: 1.0.0 | **Updated**: 2026-06-17  
> **Purpose**: Teach AI agents how to understand and operate this system correctly.  
> **Scope**: 3-machine federated system (chengzigedeAir / 5kechengdeAir / 7kecheng)

---

## 1. Identity Card

| Field | Value |
|:------|:------|
| System | AgentOS — Federated AI Exoskeleton |
| Machines | chengzigedeAir (master), 5kechengdeAir (worker), 7kecheng (worker) |
| Connection | Tailscale mesh network (100.x.x.x) |
| Dashboard | Port 9988 on each machine, launchd auto-start |
| Git Repo | `~/workbuddy-agent-os/agent-sync/` (synced to all 3 machines) |

---

## 2. Python Environment (MOST IMPORTANT)

**Never use system Python.** The correct path is:

```
$HOME/.workbuddy/binaries/python/envs/agent-os/bin/python3
```

Or use the dynamic variable (for scripts):

```bash
$MC_PYTHON
```

### Key packages installed:
- camoufox 0.4.11
- playwright 1.58.0
- uvicorn 0.46.0
- orjson 3.11.9

### Common mistakes:
- ❌ `python3 -m mc run` → ⚠️ No module named mc (needs PYTHONPATH)
- ✅ `cd $AGENT_SYNC/05_tools/07_matrix/scripts && $MC_PYTHON -m mc run ...`
- ❌ Running `pip install camoufox` → Already installed in venv
- ❌ Using `matrix nurture run` → Legacy tool, use `mc run` instead

---

## 3. Command Architecture

```
User → Dashboard (port 9988)
  → /api/matrix/nurture/start         ← 养号执行入口
    → routes/matrix.py                  ← 自动选蓝图 + 路由到机器
      → 本机: subprocess mc run         ← 模式1
      → 远程: remote_exec exec_nurture  ← 模式2 (SSH)
        → mc run                        ← 真正的执行引擎
          → mc/engine.py                ← 身份分组 + 浏览器启动
            → cdp_connector.py          ← Camoufox 启动
              → matrix_modules/nurture/* ← 原子操作
```

### Key commands for agents:

```bash
# 正确的养号执行（新路径，推荐）
cd $AGENT_SYNC/05_tools/07_matrix/scripts
$MC_PYTHON -m mc run --accounts=douyin_01 --blueprints=douyin_daily --rounds=10

# 查看账号列表
$MC_PYTHON -m mc account list

# 智能登录
$MC_PYTHON -m mc smart-login douyin_01

# 远程执行（通过 Dashboard API）
curl -X POST http://localhost:9988/api/federation/nurture \
  -H "Content-Type: application/json" \
  -d '{"machine":"7kecheng","accounts":["douyin_137"],"blueprints":["douyin_daily"],"rounds":10}'
```

---

## 4. Identity Directory Resolution

**Directory naming**: Identity dirs are named by phone number, NOT account ID:
```
identities/
├── phone_18550099569/        ← 身份目录（手机号命名）
│   ├── config.yaml
│   └── user_data/            ← 浏览器持久化数据
├── phone_15358497926/
│   ├── config.yaml
│   └── user_data/
```

**Account-to-identity mapping**: `accounts.yaml` links account IDs to identity dirs:
```yaml
- id: douyin_136               # 账号 ID
  identity_dir: phone_18550099569   # 身份目录（映射关系）
  phone: '18550099569'
  platform: douyin
  owner_machine: 7kecheng        # 所属机器
```

**How `mc run` resolves it** (`mc/engine.py:269`):
```python
# Step 1: Get identity_dir from account info
identity_dir = acct.get("identity_dir", acct["id"])  # → "phone_18550099569"

# Step 2: Strip "identities/" prefix if present
identity_dir = identity_dir.replace("identities/", "")  # → "phone_18550099569"

# Step 3: Resolve full path
full_path = IDENTITIES_ROOT / identity_dir  # → ~/.../identities/phone_18550099569/
```

**❗ NEVER look for `identities/{account_id}/`.** The directories are named by phone number.

---

## 5. Machine Routing & Blueprint Auto-Selection

### Machine routing:
Each account has an `owner_machine` field. The API auto-routes:
- Local (owner_machine == this machine) → `subprocess.Popen`
- Remote (owner_machine != this machine) → SSH via `remote_exec.py`

### Blueprint auto-selection:
| Account Platform | Default Blueprint |
|:-----------------|:------------------|
| `douyin` | `douyin_daily` |
| `xiaohongshu` | `xhs_daily` |

---

## 6. Dashboard API

The Dashboard runs on each machine (port 9988, launchd auto-start on boot).

### Key API endpoints:

| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/api/identity` | GET | Returns this machine's identity |
| `/api/machines` | GET | Returns all machines' status |
| `/api/matrix/accounts` | GET | List all accounts (federated) |
| `/api/matrix/nurture/start` | POST | Execute nurture (see usage below) |
| `/api/federation/nurture` | POST | Remote nurture execution |
| `/api/health` | GET | Health check |

### `/api/matrix/nurture/start` request format:

```json
{
  "accounts": ["douyin_01", "xhs_01"],
  "rounds": 10,
  "blueprint": "douyin_daily",        // optional, auto-detect if empty
  "machine": "7kecheng",              // optional, auto-route if empty
  "dry_run": true                     // preview only, don't execute
}
```

---

## 7. Common Pitfalls for AI Agents

| Mistake | Why | Fix |
|:--------|:----|:----|
| Using `python3` | Wrong Python (no packages) | Use `$MC_PYTHON` or absolute venv path |
| Running `matrix nurture run` | Legacy CLI, doesn't handle identity mapping | Use `mc run` instead |
| Looking for `identities/{account_id}/` | Dirs named by phone number | Check `accounts.yaml` → `identity_dir` field |
| Using `--dry-run` flag | `mc run` doesn't support it | Use API's `dry_run: true` field instead |
| Installing packages with pip | Already in agent-os venv | Use `$HOME/.workbuddy/binaries/python/envs/agent-os/bin/pip3` if needed |
| Running `mc run` from wrong directory | Module not found | Must `cd` to `$AGENT_SYNC/05_tools/07_matrix/scripts` first |
| Using CDP port 9222 | Legacy Chrome, now uses Camoufox | Default: camoufox persistence mode |

---

## 8. Quick Health Check

```bash
# Check Python venv
$HOME/.workbuddy/binaries/python/envs/agent-os/bin/python3 -c "from camoufox import AsyncCamoufox; print('OK')"

# Check mc CLI
PYTHONPATH=$AGENT_SYNC/05_tools/07_matrix/scripts $HOME/.workbuddy/binaries/python/envs/agent-os/bin/python3 -m mc --help

# Check Dashboard
curl -s --connect-timeout 3 http://localhost:9988/api/identity

# List accounts
PYTHONPATH=$AGENT_SYNC/05_tools/07_matrix/scripts $HOME/.workbuddy/binaries/python/envs/agent-os/bin/python3 -m mc account list

# Test nurture preview
curl -s -X POST http://localhost:9988/api/matrix/nurture/start \
  -H "Content-Type: application/json" \
  -d '{"accounts":["douyin_test"],"rounds":1,"dry_run":true}'
```

---

## 9. Environment Variables

| Variable | Typical Value | Purpose |
|:---------|:--------------|:--------|
| `$AGENT_SYNC` | `~/workbuddy-agent-os/agent-sync` | Synced git repo root |
| `$AGENT_LOCAL` | `~/workbuddy-agent-os/agent-local` | Local (gitignored) data |
| `$MC_PYTHON` | `~/.../agent-os/bin/python3` | Dynamic Python discovery |
| `$HOME` | `/Users/chengzige` (or `5kecheng`/`7kecheng`) | Machine-specific home |
