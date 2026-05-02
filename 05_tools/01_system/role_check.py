#!/usr/bin/env python3
"""
AgentOS 角色检查工具
所有自动化脚本在执行前调用此工具检查本机角色是否符合要求。
"""
import os
import sys
import yaml
from pathlib import Path

HOST_ID_PATH = Path.home() / "workbuddy-agent-os" / "agent-local" / "identity" / "HOST_ID.md"
LOCAL_IDENTITY_DIR = Path.home() / "workbuddy-agent-os" / "agent-local" / "identity"


def read_host_id() -> dict:
    """读取本机 HOST_ID，返回角色和能力字典"""
    if not HOST_ID_PATH.exists():
        print(f"[role_check] ⚠️ HOST_ID.md 不存在: {HOST_ID_PATH}")
        print("[role_check] 请运行 agentos init --localize 生成")
        return {"role": "unknown", "capabilities": {}}
    
    try:
        with open(HOST_ID_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 从 yaml code block 中提取能力配置
        yaml_block = None
        in_block = False
        lines = []
        for line in content.split("\n"):
            if line.strip().startswith("```yaml"):
                in_block = True
                continue
            elif line.strip().startswith("```"):
                if in_block:
                    yaml_block = "\n".join(lines)
                    break
                in_block = False
                continue
            if in_block:
                lines.append(line)
        
        # 提取角色
        role = "unknown"
        for line in content.split("\n"):
            if "角色:" in line and ":" in line:
                role_part = line.split("角色:")[-1].strip()
                if role_part:
                    role = role_part
        
        # 解析能力
        capabilities = {}
        if yaml_block:
            try:
                parsed = yaml.safe_load(yaml_block)
                if isinstance(parsed, dict):
                    capabilities = parsed
            except Exception:
                pass
        
        return {
            "role": role,
            "capabilities": capabilities,
        }
    except Exception as e:
        print(f"[role_check] ❌ 读取 HOST_ID.md 失败: {e}")
        return {"role": "unknown", "capabilities": {}}


def check_role(allowed_roles: list) -> bool:
    """
    检查本机角色是否在允许列表中。
    同时运行集群冲突检测（如果任务涉及 master 权限）。
    如果角色不匹配，打印提示并返回 False。
    """
    info = read_host_id()
    role = info["role"]
    
    if role in allowed_roles:
        # 角色通过后，额外检测集群冲突（仅限 master 级别任务）
        if "master" in allowed_roles:
            try:
                from cluster_registry import pre_task_check
                return pre_task_check(allowed_roles)
            except ImportError:
                pass
        return True
    
    print(f"[role_check] ⛔ 本机角色={role}，需要角色={allowed_roles}，跳过执行")
    print(f"[role_check] 如需修改角色，编辑 {HOST_ID_PATH}")
    return False


def check_capability(capability: str) -> bool:
    """
    检查本机是否启用指定能力。
    """
    info = read_host_id()
    caps = info.get("capabilities", {})
    
    if isinstance(caps.get(capability), bool):
        return caps[capability]
    
    # 也兼容字符串 True/False
    if isinstance(caps.get(capability), str):
        return caps[capability].lower() in ("true", "yes", "1")
    
    print(f"[role_check] ⛔ 能力 {capability} 未定义或已禁用，跳过执行")
    return False


def print_status():
    """打印本机角色状态"""
    info = read_host_id()
    print(f"[role_check] 本机角色: {info['role']}")
    print(f"[role_check] 能力配置:")
    for k, v in info.get("capabilities", {}).items():
        status = "✅" if v else "❌"
        print(f"    {status} {k}: {v}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "status":
            print_status()
        elif cmd == "check-role":
            allowed = sys.argv[2:] if len(sys.argv) > 2 else ["master"]
            if check_role(allowed):
                print(f"[role_check] ✅ 角色确认通过")
                sys.exit(0)
            else:
                sys.exit(1)
        elif cmd == "check-capability":
            cap = sys.argv[2] if len(sys.argv) > 2 else ""
            if check_capability(cap):
                print(f"[role_check] ✅ 能力确认通过: {cap}")
                sys.exit(0)
            else:
                sys.exit(1)
    else:
        print_status()
