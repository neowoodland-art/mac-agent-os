#!/bin/bash
# 2026-05-14 系统升级脚本：Peekaboo v3 + CloakBrowser
# 本脚本放在 git 仓库中，所有机器 git pull 后执行即可
set -e

echo "=== 2026-05-14 系统升级 ==="
echo ""

# 0. 同步代码
echo "[0/4] 同步代码..."
cd "$(dirname "$0")/../../../"
git pull 2>&1 | tail -2
bash 00_bootstrap/apply-config.sh 2>&1 | tail -1

# 1. 安装 Peekaboo
echo "[1/4] 安装 Peekaboo..."
npm install -g @steipete/peekaboo 2>&1 | tail -1
peekaboo permissions status 2>&1 | grep -q "Granted" && echo "  ✅ 权限已开启" || echo "  ⚠️ 请手动开启权限：系统设置 → 隐私 → 屏幕录制 + 辅助功能"

# 2. 安装 CloakBrowser
echo "[2/4] 安装 CloakBrowser..."
pip install cloakbrowser 2>&1 | tail -1
echo "  ⏳ 首次启动自动下载 ~350MB Chromium..."
/Users/chengzige/.workbuddy/binaries/python/envs/agent-os/bin/python3 -c "
from cloakbrowser import launch
b = launch(humanize=True)
print(f'  ✅ CloakBrowser 就绪 (Chromium: {b.version})')
b.close()
" 2>&1

# 3. Peekaboo token 优化配置
echo "[3/4] Peekaboo token 优化..."
mkdir -p ~/.peekaboo
if [ ! -f ~/.peekaboo/config.json ]; then
  cat > ~/.peekaboo/config.json << 'CONF'
{
  // Peekaboo 配置 — token 优化版
  "log": { "level": "error" },        // 只输出错误
  "output": { "format": "json" }       // JSON 输出节省 token
}
CONF
  echo "  ✅ 已创建 token 优化配置"
else
  echo "  ⏭ 配置已存在，跳过"
fi

# 4. 验证
echo "[4/4] 验证..."
peekaboo --version 2>&1
echo "  ✅ 升级完成"

echo ""
echo "=== 完成 ==="
echo "详细信息见: 99_system/upgrade_notes/2026-05-14_peekaboo_cloakbrowser.md"
