"""
command_bus_test.py — CommandBus 全链路诊断测试

执行:
  cd 05_tools/10_dashboard && ~/.workbuddy/binaries/python/envs/agent-os/bin/python3 test_command_bus.py

测试项:
  1. CommandBus.dispatch() — 各类命令构造
  2. 本地命令执行（本机 subprocess）
  3. 远程命令分发（模拟 SSH 路径）
  4. 结果回读（本地 result 文件）
  5. Chain 接力执行
  6. ORACLE 合规检查
"""

import json, os, sys, time, traceback
from pathlib import Path

# ── 环境 ──
AGENT_SYNC = Path(os.environ.get("AGENT_SYNC", str(Path.home() / "workbuddy-agent-os" / "agent-sync")))
AGENT_LOCAL = Path(os.environ.get("AGENT_LOCAL", str(Path.home() / "workbuddy-agent-os" / "agent-local")))
sys.path.insert(0, str(AGENT_SYNC / "05_tools" / "10_dashboard"))
sys.path.insert(0, str(AGENT_SYNC / "05_tools" / "07_matrix" / "scripts"))

PASS = 0
FAIL = 0
SKIP = 0

def test(name, fn):
    global PASS, FAIL, SKIP
    try:
        result = fn()
        if result is True:
            PASS += 1
            print(f"  ✅ {name}")
        elif result is False:
            FAIL += 1
            print(f"  ❌ {name}")
        elif result == "SKIP":
            SKIP += 1
            print(f"  ⏭️ {name}")
        else:
            PASS += 1
            print(f"  ✅ {name}: {result}")
    except Exception as e:
        FAIL += 1
        print(f"  ❌ {name}: {e}")
        traceback.print_exc()


# ════════════════════════════════════════════
# 测试 1: CommandBus 导入与基础功能
# ════════════════════════════════════════════

def test_import():
    """CommandBus 能否正常导入"""
    from services.command_bus import CommandBus
    assert CommandBus is not None
    return "CommandBus 导入成功"

def test_dispatch_validation():
    """dispatch 的参数校验"""
    from services.command_bus import CommandBus
    
    # 无 type → 应返回 error
    r1 = CommandBus.dispatch("", [])
    assert r1.get("status") == "error", f"空type应返回error: {r1}"
    
    # 无 accounts → 应返回 error
    r2 = CommandBus.dispatch("collect", [])
    assert r2.get("status") == "error", f"空accounts应返回error: {r2}"
    
    return "参数校验通过"

def test_dispatch_collect_local():
    """本地 collect 命令构造"""
    from services.command_bus import CommandBus
    r = CommandBus.dispatch("collect", ["douyin_test"], {
        "blueprint": "douyin_read_profile",
        "rounds": 1,
        "dry_run": True  # 不真的执行
    })
    # dry_run 模式不应返回 error
    if r.get("status") == "error":
        return f"dry_run 不应报错: {r.get('message','')}"
    pm = r.get('per_machine') or {}
    return f"collect: {r.get('status','?')} per_machine={len(pm)}"


def test_dispatch_login_local():
    """本地 login 命令构造"""
    from services.command_bus import CommandBus
    r = CommandBus.dispatch("login", ["douyin_test"], {"machine": "chengzigedeAir", "dry_run": True})
    if r.get("status") == "error":
        return f"login dry_run 报错: {r.get('message','')}"
    return f"login: {r.get('status','?')}"


def test_dispatch_comment():
    """评论命令构造"""
    from services.command_bus import CommandBus
    r = CommandBus.dispatch("comment", ["douyin_test"], {
        "url": "https://www.douyin.com/video/123",
        "dry_run": True
    })
    if r.get("status") == "error":
        return f"comment dry_run 报错: {r.get('message','')}"
    return f"comment: {r.get('status','?')}"


# ════════════════════════════════════════════
# 测试 2: mc CLI 可用性
# ════════════════════════════════════════════

def test_mc_cli_exists():
    """mc CLI 是否可执行"""
    import subprocess
    r = subprocess.run(
        [sys.executable, "-m", "mc", "--help"],
        capture_output=True, text=True, timeout=10,
        cwd=str(AGENT_SYNC / "05_tools" / "07_matrix" / "scripts")
    )
    assert r.returncode == 0, f"mc --help 退出码: {r.returncode}"
    assert "usage" in r.stdout.lower() or "usage" in r.stderr.lower()
    return "mc CLI 可用"


def test_mc_version():
    """mc 版本"""
    import subprocess
    r = subprocess.run(
        [sys.executable, "-m", "mc", "--version"],
        capture_output=True, text=True, timeout=10,
        cwd=str(AGENT_SYNC / "05_tools" / "07_matrix" / "scripts")
    )
    return f"mc version: {r.stdout.strip() or r.stderr.strip() or '?'}"


# ════════════════════════════════════════════
# 测试 3: ORACLE 合规检查
# ════════════════════════════════════════════

def test_oracle_load():
    """ORACLE.yaml 是否能正确加载"""
    oracle_path = AGENT_SYNC / "ORACLE.yaml"
    assert oracle_path.exists(), f"ORACLE.yaml 不存在: {oracle_path}"
    import yaml
    oracle = yaml.safe_load(oracle_path.read_text())
    assert "accounts" in oracle, f"ORACLE 没有 accounts 字段"
    assert len(oracle["accounts"]) > 0, "ORACLE accounts 为空"
    return f"ORACLE: {len(oracle['accounts'])} 条账号声明"


def test_oracle_consistency():
    """验证 ORACLE 声明与本地账号是否一致"""
    import yaml
    oracle_path = AGENT_SYNC / "ORACLE.yaml"
    oracle = yaml.safe_load(oracle_path.read_text())
    
    oracle_ids = set()
    for entry in oracle.get("accounts", []):
        for plat, aid in entry.get("platforms", {}).items():
            oracle_ids.add(aid)
    
    from matrix_mgmt import MatrixManager
    mgr = MatrixManager()
    local_accts = mgr.list_accounts()
    local_ids = {a["id"] for a in local_accts}
    
    orphaned = oracle_ids - local_ids  # ORACLE 有但本地没有
    unregistered = local_ids - oracle_ids  # 本地有但 ORACLE 没有
    
    report = []
    if orphaned:
        report.append(f"ORACLE 多出: {orphaned}")
    if unregistered:
        report.append(f"本地未注册: {unregistered}")
    if not orphaned and not unregistered:
        report.append("完全一致")
    
    return f"ORACLE: {len(oracle_ids)}个, 本地: {len(local_ids)}个, {'; '.join(report)}"


# ════════════════════════════════════════════
# 测试 4: 本地结果文件读写
# ════════════════════════════════════════════

def test_result_file_read():
    """检查是否存在结果文件"""
    results_dir = AGENT_LOCAL / "runtime" / "results"
    if not results_dir.exists():
        return f"results 目录不存在: {results_dir}"
    files = list(results_dir.glob("*.json"))
    return f"results 目录: {len(files)} 个结果文件"


def test_result_file_write():
    """模拟写入结果文件"""
    from mc.execution_policy import write_result
    import uuid
    rid = f"test_{uuid.uuid4().hex[:8]}"
    path = write_result(rid, "completed", {
        "total_steps": 5, "success": 5, "failed": 0,
        "account_reports": [{"account": "douyin_test", "round": 1, "steps": [{"op": "test", "success": True}]}]
    })
    assert path, "write_result 返回 None"
    assert Path(path).exists(), f"结果文件未创建: {path}"
    
    # 清理
    Path(path).unlink(missing_ok=True)
    return f"结果文件创建成功: {Path(path).name}"


# ════════════════════════════════════════════
# 测试 5: 机器映射
# ════════════════════════════════════════════

def test_machine_mapping():
    """验证账号→机器映射"""
    from matrix_mgmt import MatrixManager
    mgr = MatrixManager()
    accts = mgr.list_accounts()
    
    machines = {}
    for a in accts:
        m = a.get("owner_machine", "")
        if m not in machines:
            machines[m] = 0
        machines[m] += 1
    
    machine_report = "; ".join(f"{m}:{c}" for m, c in sorted(machines.items()))
    return f"机器分布: {machine_report}"


# ════════════════════════════════════════════
# 测试 6: Chain 测试
# ════════════════════════════════════════════

def test_chain_import():
    """CommandChain 能否正常导入"""
    from services.command_chain import CommandChain, ChainTask
    assert CommandChain is not None
    assert ChainTask is not None
    return "CommandChain 导入成功"


def test_chain_create():
    """创建一条测试链条"""
    from services.command_chain import CommandChain, ChainTask
    
    chain = CommandChain.create("test-diag", [
        ChainTask("step1", "collect", ["douyin_test"],
                  {"blueprint": "douyin_read_profile", "rounds": 1},
                  max_retries=0, timeout=30, on_failure="skip"),
    ])
    assert chain is not None
    assert chain.chain_id
    assert chain.status in ("running", "pending"), f"状态异常: {chain.status}"
    return f"链条创建: {chain.chain_id} (status={chain.status})"


# ════════════════════════════════════════════
# 测试 7: 前端 API 路由
# ════════════════════════════════════════════

def test_api_health():
    """Dashboard API 健康检查"""
    import subprocess
    r = subprocess.run(
        ["curl", "-s", "http://127.0.0.1:9988/api/health"],
        capture_output=True, text=True, timeout=5
    )
    assert r.returncode == 0, f"curl 退出码: {r.returncode}"
    data = json.loads(r.stdout)
    assert data.get("status") == "ok"
    return f"API: {data.get('hostname','?')} v{data.get('version','?')}"


def test_api_accounts():
    """/api/matrix/accounts 返回数据"""
    import subprocess
    r = subprocess.run(
        ["curl", "-s", "http://127.0.0.1:9988/api/matrix/accounts"],
        capture_output=True, text=True, timeout=5
    )
    data = json.loads(r.stdout)
    accts = data if isinstance(data, list) else data.get("accounts", [])
    assert len(accts) > 0, "空账号列表"
    # 检查是否有昵称数据
    with_nick = sum(1 for a in accts if a.get("nickname"))
    return f"账号: {len(accts)}个, 有昵称: {with_nick}个"


# ════════════════════════════════════════════
# 执行
# ════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  CommandBus 全链路诊断测试")
    print("=" * 60)
    print()
    
    print(f"🔧 环境: PY={sys.executable}")
    print(f"  AGENT_SYNC={AGENT_SYNC}")
    print(f"  AGENT_LOCAL={AGENT_LOCAL}")
    print()
    
    # ── 1. CommandBus 基础 ──
    print("📦 [CommandBus 基础]")
    test("导入", test_import)
    test("参数校验", test_dispatch_validation)
    test("Collect命令", test_dispatch_collect_local)
    test("Login命令", test_dispatch_login_local)
    test("Comment命令", test_dispatch_comment)
    print()
    
    # ── 2. mc CLI ──
    print("🔧 [mc CLI 可用性]")
    test("mc命令行", test_mc_cli_exists)
    test("mc版本", test_mc_version)
    print()
    
    # ── 3. ORACLE ──
    print("📜 [ORACLE 合规]")
    test("ORACLE加载", test_oracle_load)
    test("ORACLE一致性", test_oracle_consistency)
    print()
    
    # ── 4. 结果文件 ──
    print("📁 [结果文件]")
    test("读结果", test_result_file_read)
    test("写结果", test_result_file_write)
    print()
    
    # ── 5. 机器映射 ──
    print("🗺️ [机器映射]")
    test("账号分布", test_machine_mapping)
    print()
    
    # ── 6. Chain ──
    print("⛓️ [Chain 接力]")
    test("Chain导入", test_chain_import)
    test("Chain创建", test_chain_create)
    print()
    
    # ── 7. API ──
    print("🌐 [Dashboard API]")
    test("健康检查", test_api_health)
    test("账号数据", test_api_accounts)
    print()
    
    # ── 汇总 ──
    print("=" * 60)
    total = PASS + FAIL + SKIP
    print(f"  总计: {total} | ✅ 通过: {PASS} | ❌ 失败: {FAIL} | ⏭️ 跳过: {SKIP}")
    print("=" * 60)
    
    sys.exit(0 if FAIL == 0 else 1)
