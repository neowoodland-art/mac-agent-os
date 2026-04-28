#!/bin/bash
# ============================================================
# AgentOS 初始化脚本
# 用途：首次部署或换机还原时运行，创建目录结构、安装依赖、
#       填充设备信息、部署核心配置
# 使用：cd ~/agent-os/00_bootstrap && bash init.sh
# ============================================================

set -euo pipefail

# ---------- 颜色定义 ----------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ---------- 定位 agent-os 根目录 ----------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AGENT_OS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
info "AgentOS 根目录: $AGENT_OS_ROOT"

# ---------- 检测操作系统 ----------
OS_TYPE="$(uname -s)"
case "$OS_TYPE" in
    Darwin) OS_NAME="macOS"; OS_INFO="$(sw_vers -productName) $(sw_vers -productVersion)" ;;
    Linux)  OS_NAME="Linux"; OS_INFO="$(lsb_release -ds 2>/dev/null || cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2)" ;;
    *)      OS_NAME="$OS_TYPE"; OS_INFO="$OS_TYPE" ;;
esac
HOSTNAME="$(hostname)"
info "操作系统: $OS_INFO ($OS_NAME)"
info "主机名: $HOSTNAME"

# ---------- 检测 Python ----------
PYTHON_CMD=""
MANAGED_PYTHON="/Users/chengzige/.workbuddy/binaries/python/versions/3.13.12/bin/python3"
AGENTOS_PYTHON="/Users/chengzige/.workbuddy/binaries/python/envs/agent-os/bin/python3"
AGENTOS_VENV="/Users/chengzige/.workbuddy/binaries/python/envs/agent-os"

if [ -x "$AGENTOS_PYTHON" ]; then
    PYTHON_CMD="$AGENTOS_PYTHON"
    info "使用 agent-os 虚拟环境: $AGENTOS_VENV"
elif [ -x "$MANAGED_PYTHON" ]; then
    PYTHON_CMD="$MANAGED_PYTHON"
    warn "agent-os venv 不存在，使用裸 managed Python"
elif command -v python3 &>/dev/null && python3 --version &>/dev/null; then
    PYTHON_CMD="python3"
    warn "managed Python 不可用，使用系统 python3"
elif command -v python &>/dev/null && python --version &>/dev/null; then
    PYTHON_CMD="python"
fi

if [ -n "$PYTHON_CMD" ]; then
    PYTHON_PATH="$(command -v $PYTHON_CMD)"
    PYTHON_VER="$($PYTHON_CMD --version 2>&1)"
    info "Python: $PYTHON_VER ($PYTHON_PATH)"
else
    warn "未检测到 Python，部分技能将不可用"
fi

# ---------- 检测 Node.js ----------
NODE_CMD=""
if command -v node &>/dev/null; then
    NODE_CMD="node"
    NODE_PATH="$(command -v node)"
    NODE_VER="$(node --version 2>&1)"
    info "Node.js: $NODE_VER ($NODE_PATH)"
else
    warn "未检测到 Node.js，WorkBuddy 可能无法运行"
fi

# ---------- 创建目录结构 ----------
info "创建目录结构..."

DIRS=(
    "$AGENT_OS_ROOT/03_knowledge/00_inbox"
    "$AGENT_OS_ROOT/03_knowledge/01_daily"
    "$AGENT_OS_ROOT/03_knowledge/10_concepts/cs"
    "$AGENT_OS_ROOT/03_knowledge/10_concepts/ai"
    "$AGENT_OS_ROOT/03_knowledge/10_concepts/finance"
    "$AGENT_OS_ROOT/03_knowledge/10_concepts/law"
    "$AGENT_OS_ROOT/03_knowledge/10_concepts/medicine"
    "$AGENT_OS_ROOT/03_knowledge/10_concepts/physics"
    "$AGENT_OS_ROOT/03_knowledge/10_concepts/math"
    "$AGENT_OS_ROOT/03_knowledge/10_concepts/psychology"
    "$AGENT_OS_ROOT/03_knowledge/10_concepts/philosophy"
    "$AGENT_OS_ROOT/03_knowledge/10_concepts/history"
    "$AGENT_OS_ROOT/03_knowledge/10_concepts/engineering"
    "$AGENT_OS_ROOT/03_knowledge/10_concepts/design"
    "$AGENT_OS_ROOT/03_knowledge/10_concepts/business"
    "$AGENT_OS_ROOT/03_knowledge/10_concepts/personal-management"
    "$AGENT_OS_ROOT/03_knowledge/10_concepts/personal-insight"
    "$AGENT_OS_ROOT/03_knowledge/10_concepts/other"
    "$AGENT_OS_ROOT/03_knowledge/20_methods"
    "$AGENT_OS_ROOT/03_knowledge/30_facts"
    "$AGENT_OS_ROOT/03_knowledge/40_references/papers"
    "$AGENT_OS_ROOT/03_knowledge/40_references/docs"
    "$AGENT_OS_ROOT/03_knowledge/50_resources"
    "$AGENT_OS_ROOT/03_knowledge/60_opinions"
    "$AGENT_OS_ROOT/03_knowledge/90_archive/deprecated"
    "$AGENT_OS_ROOT/03_knowledge/99_system/templates"
    "$AGENT_OS_ROOT/03_knowledge/99_system/prompts"
    "$AGENT_OS_ROOT/03_knowledge/99_system/taxonomies"
    "$AGENT_OS_ROOT/03_knowledge/99_system/timelines"
    "$AGENT_OS_ROOT/04_memory/vector_db"
    "$AGENT_OS_ROOT/04_memory/logs"
    "$AGENT_OS_ROOT/04_memory/daily_summaries"
    "$AGENT_OS_ROOT/04_memory/long_term/raw"
    "$AGENT_OS_ROOT/04_memory/memory_backup"
    "$AGENT_OS_ROOT/05_tools/00_setup"
    "$AGENT_OS_ROOT/05_tools/01_system"
    "$AGENT_OS_ROOT/05_tools/02_browser"
    "$AGENT_OS_ROOT/05_tools/03_ocr"
    "$AGENT_OS_ROOT/05_tools/04_media"
    "$AGENT_OS_ROOT/05_tools/05_crawl"
    "$AGENT_OS_ROOT/05_tools/06_mobile"
    "$AGENT_OS_ROOT/06_runtime/tasks"
    "$AGENT_OS_ROOT/06_runtime/cache"
    "$AGENT_OS_ROOT/07_migration"
)

for dir in "${DIRS[@]}"; do
    mkdir -p "$dir"
done

# 空目录添加 .gitkeep（确保坚果云能同步）
for dir in "${DIRS[@]}"; do
    if [ -z "$(ls -A "$dir" 2>/dev/null)" ]; then
        touch "$dir/.gitkeep"
    fi
done

ok "目录结构创建完成"

# ---------- 安装 Python 依赖 ----------
if [ -n "$PYTHON_CMD" ]; then
    info "安装 Python 依赖..."

    # 如果 agent-os venv 不存在，自动创建
    if [ ! -d "$AGENTOS_VENV" ]; then
        info "创建 agent-os 虚拟环境..."
        if [ -x "$MANAGED_PYTHON" ]; then
            $MANAGED_PYTHON -m venv "$AGENTOS_VENV"
        else
            python3 -m venv "$AGENTOS_VENV" 2>/dev/null || warn "无法创建 venv，跳过依赖安装"
        fi
    fi

    # 使用 requirements.txt 安装
    REQ_FILE="$AGENT_OS_ROOT/requirements.txt"
    if [ -f "$REQ_FILE" ] && [ -x "$AGENTOS_PYTHON" ]; then
        $AGENTOS_PYTHON -m pip install -r "$REQ_FILE" --quiet 2>/dev/null \
            && ok "Python 依赖安装完成（来自 requirements.txt）" \
            || warn "部分依赖安装失败，请检查 requirements.txt"
    else
        warn "requirements.txt 或 venv 不存在，跳过依赖安装"
        warn "手动安装: $AGENTOS_PYTHON -m pip install -r $REQ_FILE"
    fi
fi

# ---------- 填充设备信息到 IDENTITY.md ----------
info "填充设备信息..."
IDENTITY_FILE="$AGENT_OS_ROOT/01_core/IDENTITY.md"

if [ -f "$IDENTITY_FILE" ]; then
    # 获取当前时间
    INIT_TIME="$(date '+%Y-%m-%d %H:%M:%S')"
    
    # 使用 sed 替换占位符
    sed -i.bak \
        -e "s|__HOSTNAME__|$HOSTNAME|g" \
        -e "s|__OS_INFO__|$OS_INFO|g" \
        -e "s|__AGENT_OS_PATH__|$AGENT_OS_ROOT|g" \
        -e "s|__PYTHON_PATH__|${PYTHON_PATH:-未安装}|g" \
        -e "s|__NODE_PATH__|${NODE_PATH:-未安装}|g" \
        -e "s|__INIT_TIME__|$INIT_TIME|g" \
        "$IDENTITY_FILE"
    
    rm -f "$IDENTITY_FILE.bak"
    ok "设备信息已写入 IDENTITY.md"
else
    warn "IDENTITY.md 不存在，跳过设备信息填充"
fi

# ---------- 初始化记忆体文件 ----------
info "初始化记忆体文件..."

# L1 关键词索引
KEYWORD_INDEX="$AGENT_OS_ROOT/04_memory/vector_db/keyword_index.json"
if [ ! -f "$KEYWORD_INDEX" ]; then
    cat > "$KEYWORD_INDEX" << 'EOF'
{
  "version": "1.0.0",
  "last_updated": "",
  "entries": []
}
EOF
    ok "L1 关键词索引已创建"
fi

# L2 facts.db
FACTS_DB="$AGENT_OS_ROOT/04_memory/long_term/facts.db"
if [ ! -f "$FACTS_DB" ]; then
    if [ -n "$PYTHON_CMD" ]; then
        $PYTHON_CMD -c "
import sqlite3
conn = sqlite3.connect('$FACTS_DB')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object TEXT NOT NULL,
    confidence REAL DEFAULT 0.7,
    nature TEXT DEFAULT 'fact',
    domain TEXT,
    source TEXT,
    date_created TEXT,
    date_modified TEXT,
    previous_version TEXT,
    superseded_by TEXT,
    version INTEGER DEFAULT 1
)''')
c.execute('''CREATE INDEX IF NOT EXISTS idx_facts_subject ON facts(subject)''')
c.execute('''CREATE INDEX IF NOT EXISTS idx_facts_domain ON facts(domain)''')
c.execute('''CREATE INDEX IF NOT EXISTS idx_facts_confidence ON facts(confidence)''')
conn.commit()
conn.close()
print('L2 facts.db 已创建')
"
    else
        warn "无法创建 facts.db（需要 Python），请稍后手动运行"
    fi
fi

ok "记忆体初始化完成"

# ---------- 检测坚果云同步路径 ----------
info "检测坚果云同步..."
NUTSTORE_PATHS=(
    "$HOME/Nutstore Files"
    "$HOME/坚果云"
    "$HOME/Nutstore"
)
NUTSTORE_FOUND=""
for p in "${NUTSTORE_PATHS[@]}"; do
    if [ -d "$p" ]; then
        NUTSTORE_FOUND="$p"
        break
    fi
done

if [ -n "$NUTSTORE_FOUND" ]; then
    ok "坚果云目录已找到: $NUTSTORE_FOUND"
    info "建议将 agent-os 目录放在坚果云同步文件夹内以实现跨机同步"
else
    warn "未检测到坚果云目录，如需跨机同步请手动配置"
fi

# ---------- 完成提示 ----------
echo ""
echo "========================================="
ok "AgentOS 初始化完成！"
echo "========================================="
echo ""
info "下一步操作："
echo "  1. 部署核心配置: cd $AGENT_OS_ROOT/00_bootstrap && bash apply-config.sh"
echo "  2. 导入技能包:    cd $AGENT_OS_ROOT/00_bootstrap && bash import_skills.sh"
echo "  3. 打开 Obsidian 以 $AGENT_OS_ROOT/03_knowledge/ 作为 Vault"
echo ""
info "如需跨机同步，将 $AGENT_OS_ROOT 目录移动到坚果云同步文件夹内即可"
