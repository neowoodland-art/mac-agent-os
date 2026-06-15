#!/bin/bash
#
# Matrix 矩阵养号系统 — 新机一键恢复脚本（v4.0 配置文件版）
#
# 用法:
#   bash ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/install.sh
#
# 功能:
#   1. 在 agent-local/tools/matrix/ 建立本机数据目录骨架
#   2. 生成本机 local.yaml 路径配置文件（替代软链接，解决多机同步问题）
#   3. 清理旧版软链接残留（如有）
#   4. 安装 Python 依赖
#   5. 提示初始化账号配置
#
# 设计原则 (v4.0):
#   - local.yaml 不参与坚果云同步，每台机器独立生成
#   - Python 脚本统一通过 scripts/local_paths.py 读取路径，不再依赖软链接
#   - 多机同步只需跑一次 install.sh，互不干扰
#

set -e

TOOL_DIR="$(cd "$(dirname "$0")" && pwd)"
LOCAL_DIR="$HOME/workbuddy-agent-os/agent-local/tools/matrix"
PYTHON="${WORKBUDDY_PYTHON:-$(which python3)}"

echo "=========================================="
echo "  Matrix 矩阵养号系统 — 新机恢复 (v4.0)"
echo "=========================================="
echo ""
echo "代码目录: $TOOL_DIR"
echo "本地数据: $LOCAL_DIR"
echo "Python:   $PYTHON"
echo ""

# ── Step 1: 建立本机数据目录骨架 ────────────────────────────
echo "▶ [1/5] 建立本地数据目录..."
mkdir -p "$LOCAL_DIR/config"
mkdir -p "$LOCAL_DIR/data/cookies"
mkdir -p "$LOCAL_DIR/data/camoufox_pids"
mkdir -p "$LOCAL_DIR/profiles"
mkdir -p "$LOCAL_DIR/logs"
mkdir -p "$LOCAL_DIR/screenshots"
echo "   ⚠️  注意: profiles/ 含 Chrome 登录数据，换机后需重新登录各平台账号"
echo "   ✅ $LOCAL_DIR"

# ── Step 2: 生成 local.yaml 配置文件 ─────────────────────────
echo "▶ [2/5] 生成 local.yaml 路径配置..."
CONF_FILE="$TOOL_DIR/local.yaml"
if [ -f "$CONF_FILE" ]; then
    CURRENT_ROOT=$(grep "local_data_root:" "$CONF_FILE" 2>/dev/null | sed 's/.*local_data_root: *//' | tr -d "\"'" | xargs)
    if [ "$CURRENT_ROOT" = "$LOCAL_DIR" ]; then
        echo "   ✅ local.yaml 已存在且路径正确，跳过"
    else
        echo "   ⚠️  local.yaml 存在但路径不一致: $CURRENT_ROOT"
        echo "   → 更新为当前路径: $LOCAL_DIR"
        cat > "$CONF_FILE" << EOF
# Matrix 本机数据目录配置
# 此文件由 install.sh 生成，每台机器独立，不参与坚果云同步
#
# local_data_root: 本机 agent-local/tools/matrix 目录的绝对路径

matrix:
  local_data_root: $LOCAL_DIR
EOF
        echo "   ✅ local.yaml 已更新"
    fi
else
    cat > "$CONF_FILE" << EOF
# Matrix 本机数据目录配置
# 此文件由 install.sh 生成，每台机器独立，不参与坚果云同步
#
# local_data_root: 本机 agent-local/tools/matrix 目录的绝对路径

matrix:
  local_data_root: $LOCAL_DIR
EOF
    echo "   ✅ local.yaml 已生成: $CONF_FILE"
fi

# ── Step 3: 清理旧版软链接 ───────────────────────────────────
echo "▶ [3/5] 检查旧版软链接残留..."
CLEANUP_NEEDED=0
for name in config data logs screenshots profiles; do
    LINK="$TOOL_DIR/$name"
    if [ -L "$LINK" ]; then
        TARGET=$(readlink "$LINK")
        echo "   🧹 发现旧版软链接: $name → $TARGET"
        rm "$LINK"
        echo "      已删除（路径已由 local.yaml 管理）"
        CLEANUP_NEEDED=1
    elif [ -d "$LINK" ]; then
        # 可能是坚果云展开的真实目录（含旧数据）
        echo "   ⚠️  $LINK 是真实目录（非软链接）"
        echo "      可能是坚果云同步时展开的旧软链接数据"
        echo "      建议检查内容后手动处理或删除"
    fi
done
if [ "$CLEANUP_NEEDED" -eq 0 ]; then
    echo "   ✅ 无旧版软链接残留"
fi

# ── Step 4: 安装 Python 依赖 ────────────────────────────────
echo "▶ [4/5] 安装 Python 依赖..."
if $PYTHON -m pip install -r "$TOOL_DIR/requirements.txt" -q; then
    echo "   ✅ 依赖安装完成"
    # 安装 patchright 浏览器二进制
    $PYTHON -m patchright install chromium 2>/dev/null && echo "   ✅ Chromium (patchright) 已安装" || echo "   ⚠️  Chromium 安装跳过（可稍后手动执行: python -m patchright install chromium）"
else
    echo "   ❌ 依赖安装失败，请检查 Python 环境"
    exit 1
fi

# ── Step 5: 配置模板初始化 (统一跨机模板) ──────────────────
echo "▶ [5/5] 初始化配置模板..."
CONFIG_DIR="$LOCAL_DIR/config"
TEMPLATE_DIR="$TOOL_DIR/config_template"
mkdir -p "$CONFIG_DIR"

# 从模板复制所有配置（不覆盖已有文件）
for tmpl in "$TEMPLATE_DIR"/*; do
    fname=$(basename "$tmpl")
    target="$CONFIG_DIR/$fname"
    if [ ! -f "$target" ]; then
        cp "$tmpl" "$target"
        echo "   📋 已安装: $fname"
    else
        echo "   ✅ 已存在: $fname"
    fi
done

# ── 初始化数据库 ────────────────────────────────────────────
DB_FILE="$LOCAL_DIR/data/matrix.db"
if [ ! -f "$DB_FILE" ]; then
    echo ""
    echo "▶ 初始化数据库..."
    cd "$TOOL_DIR" && $PYTHON scripts/init_db.py && echo "   ✅ 数据库已初始化" || echo "   ⚠️  数据库初始化失败，可稍后手动执行: python scripts/init_db.py"
fi

echo ""
echo "=========================================="
echo "  ✅ 安装完成！"
echo "=========================================="
echo ""
echo "使用方法:"
echo "  cd $TOOL_DIR"
echo "  python scripts/switch_account.py --method profile --target douyin_01 --port 9222"
echo "  python scripts/task_engine.py --blueprint douyin_browse_v2 --account douyin_01"
echo ""
echo "账号配置文件:"
echo "  $CONFIG_FILE"
echo ""
echo "❗ 坚果云同步提示:"
echo "   请将 local.yaml 加入坚果云排除列表，避免被同步到其他机器"
echo ""
exit 0
