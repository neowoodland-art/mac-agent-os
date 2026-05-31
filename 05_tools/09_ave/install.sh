#!/bin/bash
# ==========================================
# AVE v2.0 安装脚本
# ==========================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SYNC_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOCAL_ROOT="$SYNC_ROOT/../agent-local"

echo "=========================================="
echo "  AVE v2.0 安装"
echo "=========================================="

# 1. 创建本地目录
echo "[INFO] 创建本地数据目录..."
mkdir -p "$LOCAL_ROOT/tools/ave/config"
mkdir -p "$LOCAL_ROOT/tools/ave/cache/materials"
mkdir -p "$LOCAL_ROOT/tools/ave/cache/outputs"
mkdir -p "$LOCAL_ROOT/tools/ave/templates/remotion"

# 2. 复制配置模板（如本地不存在）
LOCAL_CONFIG="$LOCAL_ROOT/tools/ave/config/local.yaml"
if [ ! -f "$LOCAL_CONFIG" ]; then
    cp "$SCRIPT_DIR/config.yaml" "$LOCAL_CONFIG"
    echo "[WARN] 请编辑 $LOCAL_CONFIG 填入 API 密钥"
else
    echo "[OK] 本地配置已存在: $LOCAL_CONFIG"
fi

# 3. 安装 Python 依赖
echo "[INFO] 安装 Python 依赖..."
cd "$SCRIPT_DIR"
pip install -r requirements.txt.pip --quiet 2>/dev/null && \
    echo "[OK] 依赖安装完成" || \
    echo "[WARN] 部分依赖安装失败"

# 4. 验证 FFmpeg
if command -v ffmpeg &>/dev/null; then
    echo "[OK] FFmpeg 已安装: $(ffmpeg -version 2>&1 | head -1)"
else
    echo "[WARN] FFmpeg 未安装，请运行: brew install ffmpeg"
fi

echo ""
echo "=========================================="
echo "  ✅ AVE v2.0 安装完成"
echo "=========================================="
echo ""
echo "快速验证:"
echo "  python $SCRIPT_DIR/scripts/main.py --help"
echo ""
echo "下一步:"
echo "  1. 编辑 $LOCAL_CONFIG 填入 API 密钥"
echo "  2. 运行人声合成测试: python $SCRIPT_DIR/scripts/main.py voice --text '你好'"
echo ""
