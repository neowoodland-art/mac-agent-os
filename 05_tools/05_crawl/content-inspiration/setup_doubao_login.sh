#!/bin/bash
# 豆包持久化浏览器登录设置
# 运行此脚本后，在弹出的浏览器中登录豆包，然后关掉浏览器即可

cd "$(dirname "$0")"
echo "=== 豆包持久化浏览器登录设置 ==="
echo ""
echo "即将打开浏览器窗口..."
echo "请在浏览器中登录你的豆包账号"
echo "登录完成后，关掉浏览器窗口即可"
echo "以后系统将自动复用本次登录态"
echo ""

/Users/chengzige/.workbuddy/binaries/python/envs/agent-os/bin/python3 -c "
from doubao_driver import DoubaoDriver
import time

d = DoubaoDriver()
print('启动持久化浏览器...')
d._start_persistent()
d.page.goto('https://www.doubao.com/chat', timeout=30000)
time.sleep(2)

print('浏览器已打开，请登录豆包...')
print('关掉浏览器窗口后继续...')

# 等待浏览器关闭（context 断开连接）
try:
    while True:
        time.sleep(2)
        try:
            _ = d.page.title
        except:
            break
except:
    pass

print('浏览器已关闭，session 已保存')
print('位置: ~/.cloakbrowser/doubao_profile/')
"
