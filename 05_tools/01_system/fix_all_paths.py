#!/usr/bin/env python3
"""
AgentOS 路径批量修复脚本 v1.0
将所有 ~/workbuddy-agent-os/agent-sync / ~/workbuddy-agent-os/agent-local 旧路径引用替换为新的标准路径
"""
import os
import re
from pathlib import Path

SYNC_ROOT = Path.home() / "workbuddy-agent-os" / "agent-sync"

# 替换规则（按优先级排序，长匹配优先）
REPLACEMENTS = [
    # 1. 先处理长路径（避免部分替换）
    ("~/workbuddy-agent-os/agent-sync/", "~/workbuddy-agent-os/agent-sync/"),
    ("~/workbuddy-agent-os/agent-local/", "~/workbuddy-agent-os/agent-local/"),
    ("agent-sync/03_knowledge/", "agent-sync/03_knowledge/"),
    # 2. 处理没有尾部斜杠的情况
    ("~/workbuddy-agent-os/agent-local", "~/workbuddy-agent-os/agent-local"),
    ("~/workbuddy-agent-os/agent-sync", "~/workbuddy-agent-os/agent-sync"),
]

# 需要排除的目录模式
EXCLUDE_PATTERNS = [
    ".git/", "node_modules/", "__pycache__/", ".DS_Store",
    "agent-os/vector_db/", "agent-os/06_runtime/",
]

EXCLUDE_FILES = [".gitignore"]  # 跳过这些文件（手动审查）

def should_skip(filepath: str) -> bool:
    """判断是否应该跳过该文件"""
    fp = filepath.replace(str(SYNC_ROOT), "")
    for pat in EXCLUDE_PATTERNS:
        if pat in fp:
            return True
    return False

def fix_file(filepath: str) -> tuple:
    """修复单个文件，返回 (修改次数, 原始内容, 新内容)"""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        print(f"  ⚠️ 无法读取: {filepath} ({e})")
        return (0, "", "")

    original = content
    total_fixes = 0
    
    for old, new in REPLACEMENTS:
        if old in content:
            count = content.count(old)
            content = content.replace(old, new)
            total_fixes += count

    if total_fixes > 0:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    
    return (total_fixes, original, content)

def main():
    print("=" * 60)
    print("AgentOS 路径批量修复工具")
    print(f"目标目录: {SYNC_ROOT}")
    print("=" * 60)
    
    # 收集所有文本文件
    extensions = {".md", ".py", ".sh", ".json", ".yaml", ".yml", ".txt", ".cfg", ".ini", ".toml", ".conf"}
    all_fixes = {}
    total_fixes = 0
    total_files = 0
    
    for root, dirs, files in os.walk(str(SYNC_ROOT)):
        # 跳过排除目录
        dirs[:] = [d for d in dirs if not should_skip(os.path.join(root, d))]
        
        for fname in files:
            fpath = os.path.join(root, fname)
            ext = os.path.splitext(fname)[1]
            
            if ext not in extensions:
                continue
            if should_skip(fpath):
                continue
            if os.path.basename(fpath) in EXCLUDE_FILES:
                continue
                
            count, orig, new = fix_file(fpath)
            if count > 0:
                all_fixes[fpath] = count
                total_fixes += count
                total_files += 1
                print(f"  [{count}处] {fpath.replace(str(Path.home()), '~')}")

    print()
    print("=" * 60)
    print(f"✅ 批量修复完成")
    print(f"   涉及文件: {total_files}")
    print(f"   修复处数: {total_fixes}")
    print("=" * 60)
    
    # 按修改次数排序显示
    if all_fixes:
        print("\n按修复数量排名：")
        sorted_fixes = sorted(all_fixes.items(), key=lambda x: -x[1])
        for fpath, count in sorted_fixes[:10]:
            print(f"  {count:3d}处  {fpath.replace(str(Path.home()), '~')}")
    
    return total_fixes > 0

if __name__ == "__main__":
    main()
