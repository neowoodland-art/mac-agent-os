#!/bin/bash
# ============================================================
# AgentOS 初始化脚本
# 用途：首次部署或换机还原时运行，创建目录结构、安装依赖、
#       填充设备信息、部署核心配置
# 使用：cd ~/workbuddy-agent-os/agent-sync/00_bootstrap && bash init.sh
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
CURRENT_USER="$(whoami)"
MANAGED_PYTHON="$HOME/.workbuddy/binaries/python/versions/3.13.12/bin/python3"
AGENTOS_PYTHON="$HOME/.workbuddy/binaries/python/envs/agent-os/bin/python3"
AGENTOS_VENV="$HOME/.workbuddy/binaries/python/envs/agent-os"

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

# ---------- 检测环境变量 AGENT_SYNC / AGENT_LOCAL ----------
if [ -z "$AGENT_SYNC" ]; then
    export AGENT_SYNC="$HOME/workbuddy-agent-os/agent-sync"
    warn "AGENT_SYNC 未设置，默认: $AGENT_SYNC"
    # 写入 .zshrc（如果存在）
    if [ -f "$HOME/.zshrc" ]; then
        if ! grep -q "export AGENT_SYNC" "$HOME/.zshrc" 2>/dev/null; then
            echo "" >> "$HOME/.zshrc"
            echo "# AgentOS 路径变量" >> "$HOME/.zshrc"
            echo "export AGENT_SYNC=\"\$HOME/workbuddy-agent-os/agent-sync\"" >> "$HOME/.zshrc"
            echo "export AGENT_LOCAL=\"\$HOME/workbuddy-agent-os/agent-local\"" >> "$HOME/.zshrc"
            ok "已写入 .zshrc: AGENT_SYNC / AGENT_LOCAL"
        fi
    fi
else
    ok "AGENT_SYNC=$AGENT_SYNC"
fi
if [ -z "$AGENT_LOCAL" ]; then
    export AGENT_LOCAL="$HOME/workbuddy-agent-os/agent-local"
    warn "AGENT_LOCAL 未设置，默认: $AGENT_LOCAL"
fi

# ---------- 检测或创建 agent-local/config.yaml ----------
LOCAL_CONFIG="$AGENT_LOCAL/config.yaml"
if [ ! -f "$LOCAL_CONFIG" ]; then
    mkdir -p "$AGENT_LOCAL" 2>/dev/null
    cat > "$LOCAL_CONFIG" << 'CONFEOF'
# agent-local/config.yaml — 本机唯一配置入口
# 此文件每台机器独立，不同步到 Git。覆盖 ORACLE.yaml 中的默认值。

hostname: "$(hostname)"
machine_uid: ""

# 代理设置（各机器不同）
proxy:
  socks5: "socks5://127.0.0.1:10800"
  http: ""

# 浏览器窗口偏移（多账号同屏时避免重叠）
screen_offsets:
  default: {x: 0, y: 0, width: 702, height: 783}

# 端口分配（避免多机器端口冲突）
ports:
  dashboard: 9988
  camouflage_base: 9200
CONFEOF
    ok "已创建: $LOCAL_CONFIG"
else
    ok "本地配置已存在: $LOCAL_CONFIG"
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

# ---------- 创建 ~/workbuddy-agent-os/agent-local/ 本机专属目录 ----------
info "创建本机专属目录 ~/workbuddy-agent-os/agent-local/..."

LOCAL_DIRS=(
    "$HOME/workbuddy-agent-os/agent-local/identity"
    "$HOME/workbuddy-agent-os/agent-local/memory/raw"
    "$HOME/workbuddy-agent-os/agent-local/memory/vector_db"
    "$HOME/workbuddy-agent-os/agent-local/memory/daily"
    "$HOME/workbuddy-agent-os/agent-local/runtime/cache"
    "$HOME/workbuddy-agent-os/agent-local/materials/web"
    "$HOME/workbuddy-agent-os/agent-local/materials/video"
    "$HOME/workbuddy-agent-os/agent-local/materials/audio"
    "$HOME/workbuddy-agent-os/agent-local/materials/screenshots"
    "$HOME/workbuddy-agent-os/agent-local/materials/refined_for_inbox"
    "$HOME/workbuddy-agent-os/agent-local/submissions/inbox"
    "$HOME/workbuddy-agent-os/agent-local/submissions/memory_export"
)

for dir in "${LOCAL_DIRS[@]}"; do
    mkdir -p "$dir"
done
ok "本机专属目录创建完成"

# ---------- 重建软链接（agent-os-local ↔ agent-os） ----------
info "重建软链接..."

SYMLINKS=(
    "$AGENT_OS_ROOT/04_memory/long_term/raw:$HOME/workbuddy-agent-os/agent-local/memory/raw"
    "$AGENT_OS_ROOT/04_memory/vector_db:$HOME/workbuddy-agent-os/agent-local/memory/vector_db"
    "$AGENT_OS_ROOT/06_runtime/cache:$HOME/workbuddy-agent-os/agent-local/runtime/cache"
)

for entry in "${SYMLINKS[@]}"; do
    LINK_PATH="${entry%%:*}"
    TARGET_PATH="${entry##*:}"
    
    if [ -L "$LINK_PATH" ]; then
        # 已是软链接，检查目标是否存在
        if [ -e "$LINK_PATH" ]; then
            ok "软链接已存在: $(basename $LINK_PATH) → $TARGET_PATH"
        else
            warn "软链接目标不存在，重建: $LINK_PATH"
            rm -f "$LINK_PATH"
            ln -s "$TARGET_PATH" "$LINK_PATH"
        fi
    elif [ -d "$LINK_PATH" ]; then
        # 是真实目录（首次迁移后的老机器），保留不动
        ok "真实目录已存在: $LINK_PATH（未软链接）"
    else
        # 不存在，创建软链接
        mkdir -p "$(dirname "$LINK_PATH")"
        ln -s "$TARGET_PATH" "$LINK_PATH"
        ok "软链接已创建: $(basename $LINK_PATH) → $TARGET_PATH"
    fi
done

ok "软链接处理完成"

# ---------- 创建 agent-os 内部目录结构 ----------
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
    "$AGENT_OS_ROOT/04_memory/logs"
    "$AGENT_OS_ROOT/04_memory/daily_summaries"
    "$AGENT_OS_ROOT/04_memory/memory_backup"
    "$AGENT_OS_ROOT/05_tools/00_setup"
    "$AGENT_OS_ROOT/05_tools/01_system"
    "$AGENT_OS_ROOT/05_tools/01_system/reports"
    "$AGENT_OS_ROOT/05_tools/02_browser"
    "$AGENT_OS_ROOT/05_tools/03_ocr"
    "$AGENT_OS_ROOT/05_tools/04_media"
    "$AGENT_OS_ROOT/05_tools/05_crawl"
    "$AGENT_OS_ROOT/05_tools/06_mobile"
    "$AGENT_OS_ROOT/06_runtime/tasks"
    "$AGENT_OS_ROOT/07_migration"
)

for dir in "${DIRS[@]}"; do
    # 跳过已是软链接的路径
    if [ -L "$dir" ]; then
        continue
    fi
    mkdir -p "$dir"
done

# 空目录添加 .gitkeep（确保坚果云能同步）
for dir in "${DIRS[@]}"; do
    if [ -L "$dir" ]; then
        continue
    fi
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

# ---------- 生成本机身份文件（从模板） ----------
info "生成本机身份文件..."
TEMPLATE_DIR="$AGENT_OS_ROOT/01_core"
LOCAL_IDENTITY_DIR="$HOME/workbuddy-agent-os/agent-local/identity"
mkdir -p "$LOCAL_IDENTITY_DIR"

INIT_TIME="$(date '+%Y-%m-%d %H:%M:%S')"

# 从模板生成 IDENTITY.md（如果模板存在）
TEMPLATE_FILE="$TEMPLATE_DIR/IDENTITY.tpl.md"
LOCAL_IDENTITY="$LOCAL_IDENTITY_DIR/IDENTITY.md"
if [ -f "$TEMPLATE_FILE" ]; then
    cp "$TEMPLATE_FILE" "$LOCAL_IDENTITY"
    sed -i.bak \
        -e "s|__HOSTNAME__|$HOSTNAME|g" \
        -e "s|__OS_INFO__|$OS_INFO|g" \
        -e "s|__AGENT_OS_PATH__|$AGENT_OS_ROOT|g" \
        -e "s|__PYTHON_PATH__|${PYTHON_PATH:-未安装}|g" \
        -e "s|__NODE_PATH__|${NODE_PATH:-未安装}|g" \
        -e "s|__INIT_TIME__|$INIT_TIME|g" \
        "$LOCAL_IDENTITY"
    rm -f "$LOCAL_IDENTITY.bak"
    ok "IDENTITY.md 已从模板生成: $LOCAL_IDENTITY"
elif [ -f "$TEMPLATE_DIR/IDENTITY.md" ]; then
    # 兼容: 直接复制现有 IDENTITY.md
    cp "$TEMPLATE_DIR/IDENTITY.md" "$LOCAL_IDENTITY"
    ok "IDENTITY.md 已从共享配置复制"
fi

# 生成 HOST_ID.md（含角色选择）
HOST_ID_FILE="$LOCAL_IDENTITY_DIR/HOST_ID.md"
if [ ! -f "$HOST_ID_FILE" ]; then
    cat > "$HOST_ID_FILE" << HOSTEOF
# HOST_ID.md — 本机标识与角色

## 主机信息
- 主机名: $HOSTNAME
- 系统: $OS_INFO
- 角色: node
- 创建时间: $INIT_TIME

## 角色说明
| 角色 | 权限 | 执行任务 |
|------|------|---------|
| master | 读写全部协同目录 | 知识提纯/记忆汇总/核心维护 |
| maintainer | 写入提交箱 | 内容采集/本地记忆/提交有价值内容 |
| node | 只提交 | 信息采集/素材上传 |

## 能力开关
- memory_digestion: true
- knowledge_refinement: true
- content_collection: true
- knowledge_publish: true
HOSTEOF
    ok "HOST_ID.md 已创建（默认角色: node（最低权限），可手动提升为 maintainer/master）"
    warn "请检查 $HOST_ID_FILE 中的角色设置是否正确"
fi

ok "本机身份文件初始化完成"

# ---------- 初始化记忆体文件 ----------
info "初始化记忆体文件..."

# L1 关键词索引（存在 agent-local 的 vector_db 中）
VECTOR_DB_DIR="$HOME/workbuddy-agent-os/agent-local/memory/vector_db"
mkdir -p "$VECTOR_DB_DIR"
KEYWORD_INDEX="$VECTOR_DB_DIR/keyword_index.json"
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

# ---------- 检测 oMLX ----------
info "检测本地 LLM 引擎..."
OMLX_MODELS=""
if command -v curl &>/dev/null; then
    OMLX_RESP=$(curl -s --max-time 3 http://localhost:8000/v1/models -H "Authorization: Bearer omlx" 2>/dev/null || echo "")
    if echo "$OMLX_RESP" | grep -q '"data"'; then
        OMLX_MODELS=$(echo "$OMLX_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); [print(m['id']) for m in d.get('data',[])]" 2>/dev/null || echo "")
        ok "oMLX 已运行，可用模型:"
        echo "$OMLX_MODELS" | sed 's/^/    /'
    else
        warn "oMLX 未检测到，AI 分析功能将不可用"
        warn "请手动安装 oMLX: https://omlx.ai"
    fi
else
    warn "curl 不可用，跳过 oMLX 检测"
fi

# ---------- 完成提示 ----------
echo ""
echo "========================================="
ok "AgentOS 初始化完成！"
echo "========================================="
echo ""
info "换机还原检查清单："
echo "  [ ] 1. 检查本机角色: cat $HOME/workbuddy-agent-os/agent-local/identity/HOST_ID.md"
echo "  [ ] 2. 配置 GitHub/Gitee SSH 密钥（如需同步）"
echo "  [ ] 3. 安装 oMLX（本地 LLM 引擎）"
echo "  [ ] 4. 在 WorkBuddy 中配置自动化任务"
echo "  [ ] 5. 重建向量数据库: agentos rebuild-vector"
echo ""
info "目录边界说明："
echo "  ~/workbuddy-agent-os/agent-sync/  ← Git全量跟踪（知识库/技能/配置/模板）"
echo "  ~/workbuddy-agent-os/agent-local/ ← 本机专属，不同步"
echo "    ├── identity/        ← 本机身份（从模板生成）"
echo "    ├── memory/raw/      ← L3对话原文"
echo "    ├── memory/vector_db/← 向量数据库（升级后重建）"
echo "    ├── memory/daily/    ← 本机每日记忆摘要"
echo "    ├── materials/       ← 原始素材"
echo "    ├── submissions/     ← 待提交内容（inbox / memory_export）"
echo "    └── runtime/cache/   ← 临时缓存"
echo ""
info "架构文档: $AGENT_OS_ROOT/CORE-ARCHITECTURE.md"
