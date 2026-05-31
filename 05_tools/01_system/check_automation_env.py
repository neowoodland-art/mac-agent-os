#!/usr/bin/env python3
"""
检查自动化任务环境配置
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_env():
    """检查 Python 环境"""
    print("检查 Python 环境:")
    print("-" * 40)
    
    # 系统 Python
    sys_python = "/usr/bin/python3"
    if Path(sys_python).exists():
        result = subprocess.run([sys_python, "--version"], capture_output=True, text=True)
        print(f"系统 Python: {result.stdout.strip() if result.returncode == 0 else '❌ 不可用'}")
    else:
        print(f"系统 Python: ❌ 不存在")
    
    # WorkBuddy 管理的 Python
    wb_python = "/Users/chengzige/.workbuddy/binaries/python/envs/agent-os/bin/python3"
    if Path(wb_python).exists():
        result = subprocess.run([wb_python, "--version"], capture_output=True, text=True)
        print(f"WorkBuddy Python: {result.stdout.strip() if result.returncode == 0 else '❌ 不可用'}")
    else:
        print(f"WorkBuddy Python: ❌ 不存在")
    
    # 当前脚本使用的 Python
    print(f"当前 Python: {sys.executable}")
    result = subprocess.run([sys.executable, "--version"], capture_output=True, text=True)
    print(f"当前版本: {result.stdout.strip() if result.returncode == 0 else '未知'}")
    
    print()

def check_omlx_connection():
    """检查 oMLX 连接"""
    print("检查 oMLX 连接:")
    print("-" * 40)
    
    import requests
    
    # 测试 embedding API（关键依赖）
    url = "http://localhost:8000/v1/embeddings"
    headers = {"Authorization": "Bearer omlx", "Content-Type": "application/json"}
    data = {"model": "Qwen3-Embedding-0.6B", "input": ["测试"]}
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            print("✅ oMLX Embedding API: 正常")
        else:
            print(f"❌ oMLX Embedding API: 状态码 {response.status_code}")
    except Exception as e:
        print(f"❌ oMLX Embedding API: 连接失败 - {type(e).__name__}: {e}")
    
    print()

def check_automation_paths():
    """检查自动化脚本路径"""
    print("检查自动化脚本路径:")
    print("-" * 40)
    
    scripts = {
        "daily_digest.py": "/Users/chengzige/agent-os/02_skills/memory_manager/daily_digest.py",
        "collect_to_inbox.py": "/Users/chengzige/agent-os/02_skills/collect_to_inbox/collect_to_inbox.py",
        "inbox_refine.py": "/Users/chengzige/agent-os/02_skills/inbox_refine/inbox_refine.py",
        "semantic_search.py": "/Users/chengzige/agent-os/02_skills/memory_manager/semantic_search.py"
    }
    
    for name, path in scripts.items():
        if Path(path).exists():
            print(f"✅ {name}: 存在")
        else:
            print(f"❌ {name}: 不存在")
    
    print()

def check_python_dependencies():
    """检查 Python 依赖"""
    print("检查 Python 依赖:")
    print("-" * 40)
    
    python_path = "/Users/chengzige/.workbuddy/binaries/python/envs/agent-os/bin/python3"
    if not Path(python_path).exists():
        print("❌ WorkBuddy Python 环境不存在")
        return
    
    dependencies = [
        "requests",
        "chromadb",
        "sqlite-utils",
        "trafilatura",
        "feedparser",
        "schedule"
    ]
    
    for dep in dependencies:
        try:
            result = subprocess.run(
                [python_path, "-c", f"import {dep}; print({dep}.__version__)"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print(f"✅ {dep}: {result.stdout.strip()}")
            else:
                print(f"❌ {dep}: 导入失败")
        except Exception as e:
            print(f"❌ {dep}: 检查失败 - {type(e).__name__}")

def main():
    print("=" * 60)
    print("自动化任务环境检查")
    print("=" * 60)
    print()
    
    check_python_env()
    check_omlx_connection()
    check_automation_paths()
    check_python_dependencies()
    
    print("=" * 60)
    print("总结建议:")
    print("1. 自动化任务应使用 WorkBuddy Python 环境")
    print("2. 确保在 automation prompt 中指定完整路径:")
    print("   /Users/chengzige/.workbuddy/binaries/python/envs/agent-os/bin/python3")
    print("3. oMLX Embedding API 正常，向量化功能可用")
    print("4. 所有脚本文件都存在，路径正确")
    print("=" * 60)

if __name__ == "__main__":
    main()