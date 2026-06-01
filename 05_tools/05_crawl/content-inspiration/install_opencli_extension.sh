#!/bin/bash
# OpenCLI 安装脚本 — 新机器一键部署
set -e
echo "=== OpenCLI 安装脚本 ==="
echo ""

NODE=$(which node 2>/dev/null || echo "/Users/chengzige/.workbuddy/binaries/node/versions/22.12.0/bin/node")
if [ ! -x "$NODE" ]; then echo "❌ Node.js 未找到"; exit 1; fi
echo "  Node: $($NODE --version)"

echo "[2/4] 安装 OpenCLI..."
npm install -g @jackwener/opencli 2>&1 | tail -1

echo "[3/4] 下载 Chrome 扩展..."
EXT_DIR="$HOME/opencli-extension"
if [ -f "$EXT_DIR/manifest.json" ]; then
    echo "  扩展已存在，跳过下载"
else
    mkdir -p "$EXT_DIR"
    curl -L -o /tmp/opencli-ext.zip "https://github.com/jackwener/OpenCLI/releases/download/v1.7.12/opencli-extension-v1.0.5.zip"
    unzip -o /tmp/opencli-ext.zip -d "$EXT_DIR" 2>&1 | tail -1
    echo "  ✅ 下载完成: $EXT_DIR"
fi

echo "[4/4] 启动 daemon..."
opencli daemon restart 2>&1 | head -1

echo ""
echo "=== 完成 ==="
echo "下一步："
echo "  1. 打开 Chrome → chrome://extensions/"
echo "  2. 开启开发者模式"
echo "  3. 加载已解包扩展 → 选择 $EXT_DIR"
echo "  4. 验证: opencli doctor"
