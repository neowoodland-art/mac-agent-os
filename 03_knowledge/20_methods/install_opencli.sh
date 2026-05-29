#!/bin/bash
# ───────────────────────────────────────────────
# OpenCLI + Chrome 扩展 一键安装脚本
# 用于 AgentOS 其他节点快速部署
# ───────────────────────────────────────────────

set -e

echo "═══════════════════════════════════"
echo " OpenCLI — 自动安装"
echo "═══════════════════════════════════"

# 依赖检查
echo ""
echo "=== 依赖检查 ==="
NODE=$(which node 2>/dev/null || echo "")
if [ -z "$NODE" ]; then
    echo "❌ Node.js 未安装，请先安装 Node.js >= 20"
    exit 1
fi
echo "  Node: $(node --version)"
echo "  npm: $(npm --version)"
echo "  Chrome: $(/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version 2>/dev/null || echo '⚠️  未找到')"

# 安装/升级 CLI
echo ""
echo "=== 1. 安装/升级 OpenCLI ==="
npm install -g @jackwener/opencli
echo "  ✅ CLI: $(opencli --version 2>/dev/null || echo '?')"

# 下载扩展
echo ""
echo "=== 2. 下载 Chrome 扩展 ==="
EXT_DIR="$HOME/.opencli/extension"
mkdir -p "$EXT_DIR"
curl -sL "https://github.com/jackwener/OpenCLI/releases/download/v1.8.0/opencli-extension-v1.0.15.zip" \
  -o /tmp/opencli-ext.zip
unzip -qo /tmp/opencli-ext.zip -d "$EXT_DIR"
rm /tmp/opencli-ext.zip
echo "  ✅ 扩展已下载到: $EXT_DIR"

# 创建启动脚本
echo ""
echo "=== 3. 创建 Chrome 启动脚本 ==="
SCRIPT="$HOME/.opencli/start_chrome_with_opencli.sh"
cat > "$SCRIPT" << 'CHROME_SCRIPT'
#!/bin/bash
# 启动 Chrome（加载 OpenCLI 扩展）
EXT_DIR="$HOME/.opencli/extension"
pkill -f "Google Chrome" 2>/dev/null
sleep 1
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --load-extension="$EXT_DIR" \
  --remote-debugging-port=0 &
echo "Chrome 已启动（OpenCLI 扩展已加载）"
CHROME_SCRIPT
chmod +x "$SCRIPT"
echo "  ✅ 启动脚本: $SCRIPT"

# 启动 Chrome + 扩展
echo ""
echo "=== 4. 启动 Chrome + 扩展 ==="
bash "$SCRIPT"
sleep 4

# 验证
echo ""
echo "=== 5. 验证 ==="
opencli doctor

echo ""
echo "═══════════════════════════════════"
echo " ✅ OpenCLI 安装完成！"
echo "═══════════════════════════════════"
echo ""
echo "后续使用："
echo "  opencli daemon start              # 启动守护进程"
echo "  bash ~/.opencli/start_chrome_with_opencli.sh  # 启动Chrome+扩展"
echo "  opencli zhihu hot --limit 5       # 采集知乎热搜"
echo "  opencli xiaohongshu search AI     # 搜索小红书"
echo ""
