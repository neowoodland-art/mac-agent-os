#!/bin/bash
# agentos CLI 安装脚本
# 将 agentos 安装到 ~/.local/bin/ 并将其添加到 PATH

set -euo pipefail

AGENTOS_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$HOME/.local/bin"

echo "========================================="
echo "  AgentOS CLI 安装"
echo "========================================="
echo ""
echo "来源: $AGENTOS_DIR"
echo "目标: $INSTALL_DIR/agentos"
echo ""

# 创建 ~/.local/bin/
mkdir -p "$INSTALL_DIR"

# 创建入口脚本
cat > "$INSTALL_DIR/agentos" << 'ENTRYEOF'
#!/usr/bin/env python3
"""agentos CLI 入口：自动定位到 agent-sync 并启动主程序"""

import sys
import os
from pathlib import Path

# 尝试定位 agent-sync 根目录
CANDIDATES = [
    os.environ.get("AGENT_SYNC_ROOT"),
    str(Path.home() / "workbuddy-agent-os" / "agent-sync"),
    str(Path.home() / "agent-os"),
]

AGENTOS_MODULE = None
for root in CANDIDATES:
    if root:
        module_path = Path(root) / "05_tools" / "00_setup" / "agentos"
        if module_path.exists() and (module_path / "main.py").exists():
            AGENTOS_MODULE = str(module_path)
            break

if not AGENTOS_MODULE:
    print("❌ 无法定位 AgentOS 模块。请设置环境变量 AGENT_SYNC_ROOT")
    sys.exit(1)

sys.path.insert(0, str(Path(AGENTOS_MODULE).parent))
from agentos.main import main
main()
ENTRYEOF

chmod +x "$INSTALL_DIR/agentos"

# 检查 PATH 是否包含 ~/.local/bin
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo "⚠️  请将 ~/.local/bin 添加到 PATH:"
    echo ""
    echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc"
    echo "  source ~/.zshrc"
    echo ""
fi

echo "✅ 安装完成！"
echo ""
echo "运行测试: agentos --version"
echo "帮助:    agentos --help"
echo ""
