#!/bin/bash
# fix_ssh_auth.sh — 修复 SSH 公钥认证权限
# 在远程机器上执行一次，解决 Permission denied (publickey)
# 用法: bash fix_ssh_auth.sh

set -e

echo "=== 1. 修复目录/文件权限 ==="

# 家目录不能 group/others 可写
chmod go-w "$HOME"
echo "  ~ ($HOME) → $(stat -f '%A' "$HOME")"

# .ssh 目录
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"
echo "  ~/.ssh → $(stat -f '%A' "$HOME/.ssh")"

# authorized_keys
if [ -f "$HOME/.ssh/authorized_keys" ]; then
  chmod 600 "$HOME/.ssh/authorized_keys"
  echo "  ~/.ssh/authorized_keys → $(stat -f '%A' "$HOME/.ssh/authorized_keys")"
else
  echo "  ⚠️  ~/.ssh/authorized_keys 不存在，请先添加公钥"
fi

echo ""
echo "=== 2. 重启 SSH 服务 ==="
sudo launchctl unload /System/Library/LaunchDaemons/ssh.plist 2>/dev/null || true
sudo launchctl load -w /System/Library/LaunchDaemons/ssh.plist 2>/dev/null || true
echo "  SSH 服务已重启"

echo ""
echo "=== 3. 验证 ==="
echo "  远程登录: Remote Login $(sudo systemsetup -getremotelogin 2>/dev/null | grep -o 'On\|Off')"
echo "  端口 22: $(nc -z -v -G 2 localhost 22 2>&1 && echo '✓ 监听中' || echo '✗ 未监听')"

echo ""
echo "=== 完成 ==="
echo "从本机测试: ssh -i ~/.ssh/id_ed25519a 7kecheng@192.168.31.101"
