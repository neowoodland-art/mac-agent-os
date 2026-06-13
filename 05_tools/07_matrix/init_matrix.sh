#!/bin/bash
# ==============================================================
# Matrix 环境检测 & 初始化脚本 v5.2
#
# 流程：
#   1. 检测环境 → 输出报告
#   2. 用户确认 → 执行修复
#   3. 验证结果
#
# 用法:
#   bash init_matrix.sh              # 完整流程
#   bash init_matrix.sh --check      # 仅检测，不执行
#   bash init_matrix.sh --apply      # 跳过检测，直接执行
# ==============================================================

set -e
MODE="${1:-full}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_SYNC_DIR="$(cd "$SCRIPT_DIR/../.." 2>/dev/null && pwd || echo "$HOME/workbuddy-agent-os/agent-sync")"
AGENT_LOCAL_DIR="$HOME/workbuddy-agent-os/agent-local"
MATRIX_CODE="$AGENT_SYNC_DIR/05_tools/07_matrix"
DASHBOARD_DIR="$AGENT_SYNC_DIR/05_tools/10_dashboard"
PLIST="$HOME/Library/LaunchAgents/com.agentos.dashboard.plist"

# ═══════════════════════════════════════════════════════════
# 检测函数
# ═══════════════════════════════════════════════════════════

check_python() {
    local candidates=(
        "$HOME/.workbuddy/binaries/python/envs/agent-os/bin/python3"
        "$HOME/.workbuddy/binaries/python/envs/dashboard/bin/python"
        "$(which python3 2>/dev/null || echo "")"
    )
    for p in "${candidates[@]}"; do
        if [ -n "$p" ] && [ -x "$p" ]; then
            echo "$p"
            return 0
        fi
    done
    return 1
}

check_module() {
    local module="$1"
    local py="$2"
    "$py" -c "import $module" 2>/dev/null && return 0 || return 1
}

check_file() {
    [ -f "$1" ] && return 0 || return 1
}

check_dir() {
    [ -d "$1" ] && return 0 || return 1
}

check_launchd() {
    if [ -f "$PLIST" ]; then
        # 检查 plist 中的 Python 路径是否和当前环境匹配
        local plist_py=$(grep -A1 'ProgramArguments' "$PLIST" 2>/dev/null | grep -v "ProgramArguments\|--\|array\|string" | head -1 | sed 's/.*<string>//;s/<\/string>.*//')
        if [ -n "$plist_py" ] && [ -x "$plist_py" ]; then
            if launchctl list | grep -q "com.agentos.dashboard" 2>/dev/null; then
                echo "running"
            else
                echo "stopped"
            fi
        else
            echo "broken_path"
        fi
    else
        echo "missing"
    fi
}

check_git() {
    if [ -d "$AGENT_SYNC_DIR/.git" ]; then
        cd "$AGENT_SYNC_DIR"
        local behind=$(git rev-list HEAD..@{u} 2>/dev/null | wc -l)
        if [ "$behind" -gt 0 ]; then
            echo "behind($behind)"
        else
            echo "uptodate"
        fi
    else
        echo "norepo"
    fi
}

# ═══════════════════════════════════════════════════════════
# 阶段1：检测环境
# ═══════════════════════════════════════════════════════════

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║     Matrix 环境检测 v5.2                        ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

PYTHON=$(check_python)
ISSUES=0
FIXES=""

echo "📋 ─── 1. 基础环境 ───"
echo -n "  Python 3:          "
if [ -n "$PYTHON" ]; then
    echo "✅ $($PYTHON --version 2>&1)"
else
    echo "❌ 未找到"
    ISSUES=$((ISSUES+1))
    FIXES="$FIXES\n  - 安装 Python 3"
fi

echo -n "  代码仓库:          "
GIT_STATUS=$(check_git)
case "$GIT_STATUS" in
    uptodate)   echo "✅ 已是最新" ;;
    behind*)    echo "⚠️  落后远程 $(echo $GIT_STATUS | grep -oP '\d+') 个提交"
                FIXES="$FIXES\n  - git pull 拉取更新" ;;
    norepo)     echo "❌ 未克隆"
                ISSUES=$((ISSUES+1))
                FIXES="$FIXES\n  - git clone 克隆仓库" ;;
esac

echo ""
echo "📦 ─── 2. Python 依赖 ───"
DEPS=("httpx" "yaml" "fastapi" "uvicorn" "playwright")
DEP_NAMES=("httpx" "pyyaml" "fastapi" "uvicorn" "playwright")
MISSING_DEPS=()
for i in "${!DEPS[@]}"; do
    echo -n "  ${DEP_NAMES[$i]}:        "
    if check_module "${DEPS[$i]}" "$PYTHON"; then
        echo "✅"
    else
        echo "❌"
        MISSING_DEPS+=("${DEP_NAMES[$i]}")
    fi
done
if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    ISSUES=$((ISSUES+1))
    FIXES="$FIXES\n  - pip install ${MISSING_DEPS[*]}"
fi

echo -n "  Camoufox:          "
if check_module "camoufox" "$PYTHON"; then
    echo "✅"
else
    echo "❌"
    FIXES="$FIXES\n  - pip install camoufox && python -m camoufox fetch"
fi

echo ""
echo "📁 ─── 3. 目录结构 ───"
for d in \
    "$AGENT_LOCAL_DIR/tools/matrix/config" \
    "$AGENT_LOCAL_DIR/tools/matrix/identities" \
    "$AGENT_LOCAL_DIR/tools/matrix/data" \
    "$AGENT_LOCAL_DIR/tools/matrix/recordings"; do
    name=$(basename "$(dirname "$d")")/$(basename "$d")
    echo -n "  agent-local/$name: "
    if check_dir "$d"; then echo "✅"; else echo "❌"; FIXES="$FIXES\n  - mkdir -p $d"; fi
done

echo ""
echo "⚙️  ─── 4. 配置文件 ───"
CONFIGS=(
    "$AGENT_LOCAL_DIR/tools/matrix/config/accounts.yaml:账号配置"
    "$MATRIX_CODE/config/sms.yaml:短信API"
    "$MATRIX_CODE/config/ai.yaml:AI配置"
    "$MATRIX_CODE/config/schedule.yaml:定时任务"
    "$AGENT_LOCAL_DIR/tools/matrix/data/profiles.json:人设数据"
)
for entry in "${CONFIGS[@]}"; do
    path="${entry%%:*}"
    label="${entry##*:}"
    echo -n "  $label:        "
    if check_file "$path"; then
        echo "✅"
    else
        echo "❌（将从模板创建）"
        FIXES="$FIXES\n  - cp config_template/xxx $path"
    fi
done

echo ""
echo "🔧 ─── 5. 系统服务 ───"
echo -n "  mc 命令:           "
if command -v mc &>/dev/null; then
    local_mc=$(which mc)
    repo_mc="$MATRIX_CODE/mc"
    if [ "$local_mc" = "$repo_mc" ] || [ "$(readlink "$local_mc" 2>/dev/null)" = "$repo_mc" ]; then
        echo "✅ $local_mc"
    else
        echo "⚠️  $local_mc（指向其他位置）"
        FIXES="$FIXES\n  - ln -sf $repo_mc /usr/local/bin/mc"
    fi
else
    echo "❌"
    FIXES="$FIXES\n  - ln -sf $MATRIX_CODE/mc /usr/local/bin/mc"
fi

echo -n "  mc 包装器路径:     "
if grep -q "/Users/5kecheng\|/Users/chengzige" "$MATRIX_CODE/mc" 2>/dev/null; then
    echo "❌ 含硬编码路径"
    FIXES="$FIXES\n  - git checkout -- 05_tools/07_matrix/mc（恢复自动检测版本）"
else
    echo "✅ 自动检测"
fi

echo -n "  Dashboard 服务:    "
L_STATUS=$(check_launchd)
case "$L_STATUS" in
    running)    echo "✅ 运行中" ;;
    stopped)    echo "⚠️  已停止"
                FIXES="$FIXES\n  - launchctl kickstart com.agentos.dashboard" ;;
    broken_path)
                local broken_py=$(grep -A1 'ProgramArguments' "$PLIST" 2>/dev/null | grep -v "ProgramArguments\|--\|array\|string" | head -1 | sed 's/.*<string>//;s/<\/string>.*//')
                echo "❌ Python 路径错误: $broken_py"
                FIXES="$FIXES\n  - 运行本脚本自动修复 plist" ;;
    missing)    echo "❌ 未配置"
                FIXES="$FIXES\n  - 运行本脚本自动创建 plist" ;;
esac

echo ""
echo "📊 ─── 6. 蓝图 & 语料库 ───"
BP_COUNT=$(ls "$MATRIX_CODE/blueprints/"*.json 2>/dev/null | wc -l)
echo -n "  蓝图文件:          "
if [ "$BP_COUNT" -gt 0 ]; then echo "✅ $BP_COUNT 个"; else echo "❌"; fi

echo -n "  语料库(抖音):      "
if [ -f "$MATRIX_CODE/corpus/douyin.yaml" ]; then echo "✅"; else echo "❌"; fi

echo -n "  语料库(小红书):    "
if [ -f "$MATRIX_CODE/corpus/xiaohongshu.yaml" ]; then echo "✅"; else echo "❌"; fi

# ═══════════════════════════════════════════════════════════
# 检测汇总
# ═══════════════════════════════════════════════════════════

echo ""
echo "╔══════════════════════════════════════════════════╗"
if [ "$ISSUES" -eq 0 ] && [ -z "$FIXES" ]; then
    echo "║   ✅ 环境检查通过，无需修复                    ║"
    echo "╚══════════════════════════════════════════════════╝"
    exit 0
fi

echo "║   ⚠️  发现以下问题:                              ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo -e "$FIXES" | while read line; do
    [ -n "$line" ] && echo "  $line"
done

echo ""
if [ "$MODE" = "--check" ]; then
    echo "🔍 检测模式，未执行任何操作。"
    echo "   执行 bash init_matrix.sh 开始修复。"
    exit 0
fi

# ═══════════════════════════════════════════════════════════
# 阶段2：用户确认
# ═══════════════════════════════════════════════════════════

echo "════════════════════════════════════════════════"
echo "即将执行以下操作："
echo ""
[ -n "$(echo -e "$FIXES" | grep "git pull\|git clone")" ] && echo "  • 拉取/克隆代码仓库"
[ -n "$(echo -e "$FIXES" | grep "pip install")" ] && echo "  • 安装 Python 依赖"
[ -n "$(echo -e "$FIXES" | grep "mkdir")" ] && echo "  • 创建目录结构"
[ -n "$(echo -e "$FIXES" | grep "cp config_template")" ] && echo "  • 从模板创建配置文件"
[ -n "$(echo -e "$FIXES" | grep "ln -sf")" ] && echo "  • 安装 mc 命令"
[ -n "$(echo -e "$FIXES" | grep "plist\|launchctl")" ] && echo "  • 修复 Dashboard 启动配置"
[ -n "$(echo -e "$FIXES" | grep "git checkout.*mc")" ] && echo "  • 修复 mc 包装器硬编码路径"
echo ""
echo -n "确认执行？(y/N): "
read confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ] && [ "$confirm" != "yes" ]; then
    echo "已取消"
    exit 0
fi

# ═══════════════════════════════════════════════════════════
# 阶段3：执行修复
# ═══════════════════════════════════════════════════════════

echo ""
echo "🛠 开始修复..."

# 1. 拉取代码
if [ -d "$AGENT_SYNC_DIR/.git" ]; then
    echo "  📦 git pull..."
    cd "$AGENT_SYNC_DIR" && git pull 2>/dev/null || true
else
    echo "  📦 git clone..."
    mkdir -p "$HOME/workbuddy-agent-os"
    cd "$HOME/workbuddy-agent-os"
    git clone git@github.com:neowoodland-art/mac-agent-os.git agent-sync 2>/dev/null || \
    git clone git@gitee.com:babycalf/mac-agent-os.git agent-sync 2>/dev/null || true
    AGENT_SYNC_DIR="$HOME/workbuddy-agent-os/agent-sync"
    MATRIX_CODE="$AGENT_SYNC_DIR/05_tools/07_matrix"
    DASHBOARD_DIR="$AGENT_SYNC_DIR/05_tools/10_dashboard"
fi

# 2. 创建目录
echo "  📁 创建目录..."
mkdir -p "$AGENT_LOCAL_DIR/tools/matrix/config"
mkdir -p "$AGENT_LOCAL_DIR/tools/matrix/identities"
mkdir -p "$AGENT_LOCAL_DIR/tools/matrix/data"
mkdir -p "$AGENT_LOCAL_DIR/tools/matrix/recordings"
mkdir -p "$AGENT_LOCAL_DIR/tools/matrix/logs"

# 3. 安装依赖
echo "  📦 安装 Python 依赖..."
$PYTHON -m pip install -q --upgrade pip 2>/dev/null || true
for dep in httpx pyyaml requests fastapi uvicorn playwright; do
    $PYTHON -m pip install -q "$dep" 2>/dev/null || true
done
if [ -f "$MATRIX_CODE/requirements.txt" ]; then
    $PYTHON -m pip install -q -r "$MATRIX_CODE/requirements.txt" 2>/dev/null || true
fi
if ! check_module "camoufox" "$PYTHON"; then
    echo "  📥 安装 Camoufox..."
    $PYTHON -m pip install -q camoufox 2>/dev/null || true
    $PYTHON -m camoufox fetch 2>&1 | tail -1 || true
fi

# 4. 创建配置
echo "  ⚙️  创建配置文件..."
[ ! -f "$AGENT_LOCAL_DIR/tools/matrix/config/accounts.yaml" ] && \
    cp "$MATRIX_CODE/config_template/accounts.yaml" "$AGENT_LOCAL_DIR/tools/matrix/config/accounts.yaml" && \
    echo "    ✅ accounts.yaml"
[ ! -f "$MATRIX_CODE/config/sms.yaml" ] && \
    cp "$MATRIX_CODE/config_template/sms.yaml" "$MATRIX_CODE/config/sms.yaml" 2>/dev/null && \
    echo "    ✅ sms.yaml"
[ ! -f "$MATRIX_CODE/config/ai.yaml" ] && \
    cp "$MATRIX_CODE/config_template/ai.yaml" "$MATRIX_CODE/config/ai.yaml" 2>/dev/null && \
    echo "    ✅ ai.yaml"
[ ! -f "$MATRIX_CODE/config/schedule.yaml" ] && \
    cp "$MATRIX_CODE/config_template/schedule.yaml" "$MATRIX_CODE/config/schedule.yaml" 2>/dev/null && \
    echo "    ✅ schedule.yaml"
[ ! -f "$AGENT_LOCAL_DIR/tools/matrix/data/profiles.json" ] && \
    cp "$MATRIX_CODE/config_template/profiles.json" "$AGENT_LOCAL_DIR/tools/matrix/data/profiles.json" 2>/dev/null && \
    echo "    ✅ profiles.json"

# 5. 修复 mc 包装器
if grep -q "/Users/5kecheng\|/Users/chengzige" "$MATRIX_CODE/mc" 2>/dev/null; then
    echo "  🔧 修复 mc 包装器..."
    cd "$AGENT_SYNC_DIR" && git checkout -- 05_tools/07_matrix/mc
fi
if ! command -v mc &>/dev/null; then
    sudo ln -sf "$MATRIX_CODE/mc" /usr/local/bin/mc 2>/dev/null || true
fi

# 6. 修复 launchd
echo "  🚀 修复 Dashboard 启动配置..."
launchctl bootout gui/$(id -u)/com.agentos.dashboard 2>/dev/null || true
cat > "$PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agentos.dashboard</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>-m</string>
        <string>uvicorn</string>
        <string>app:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>9988</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$DASHBOARD_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/dashboard_launchd.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/dashboard_launchd_err.log</string>
    <key>ThrottleInterval</key>
    <integer>5</integer>
</dict>
</plist>
EOF

launchctl bootstrap gui/$(id -u) "$PLIST" 2>/dev/null || \
launchctl kickstart -k gui/$(id -u)/com.agentos.dashboard 2>/dev/null || true

# ═══════════════════════════════════════════════════════════
# 阶段4：验证
# ═══════════════════════════════════════════════════════════

echo ""
# 清除 Python 缓存（防止旧 .pyc 影响）
echo "  🧹 清除 Python 缓存..."
find "$AGENT_SYNC_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$AGENT_SYNC_DIR" -name "*.pyc" -delete 2>/dev/null || true

echo "🔍 验证..."
sleep 4

echo -n "  Dashboard: "
if curl -s http://localhost:9988/api/matrix/recordings/status >/dev/null 2>&1; then
    echo "✅ http://localhost:9988"
else
    echo "⚠️  检查日志: tail -20 /tmp/dashboard_launchd.log"
fi

echo -n "  mc task:    "
if $PYTHON -c "from mc.task import Task" 2>/dev/null; then echo "✅"; else echo "⚠️"; fi

echo -n "  定时调度:   "
if $PYTHON -c "from mc.scheduler import load_schedules" 2>/dev/null; then echo "✅"; else echo "⚠️"; fi

echo -n "  人设系统:   "
if $PYTHON -c "from mc.corpus import CorpusManager; CorpusManager()" 2>/dev/null; then echo "✅"; else echo "⚠️"; fi

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   ✅ 初始化完成                                 ║"
echo "║   Dashboard: http://localhost:9988              ║"
echo "╚══════════════════════════════════════════════════╝"
