#!/bin/bash
# 豆包驱动测试脚本
# 执行前请确保已在 Chrome 中登录 doubao.com
set -e

cd "$(dirname "$0")"

echo "=== 豆包驱动测试 ==="
echo ""
echo "请先确认：Chrome 已登录 doubao.com ✅"
read -p "按回车继续..."

echo ""
echo "测试 1: 打开豆包并检查登录状态..."
/Users/chengzige/.workbuddy/binaries/python/envs/agent-os/bin/python3 -c "
from doubao_driver import DoubaoDriver
d = DoubaoDriver()
d._start_browser()
d.page.goto('https://www.doubao.com/chat', timeout=30000)
ok = d._ensure_logged_in()
print(f'登录状态: {\"✅ 已登录\" if ok else \"❌ 未登录\"}')
if ok:
    inp = d._find_input()
    print(f'输入框: {\"✅ 找到\" if inp else \"❌ 未找到\"}')
    if inp:
        print(f'  placeholder: {inp.get_attribute(\"placeholder\")}')
d._close_browser()
" 2>&1

echo ""
echo "完成"
