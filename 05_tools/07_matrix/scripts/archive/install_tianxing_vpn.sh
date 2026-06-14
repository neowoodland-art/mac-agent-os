#!/bin/bash
# ─── 天行 L2TP VPN 配置（macOS 26 兼容版）───

# macOS 26 已移除 networksetup 的 L2TP 命令，改用 .mobileconfig 配置描述文件

UUID1=$(uuidgen)
UUID2=$(uuidgen)
PROFILE_NAME="TianXing-L2TP.mobileconfig"
PROFILE_PATH="$HOME/Desktop/$PROFILE_NAME"

cat > "$PROFILE_PATH" << MOBILECONFIG
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>PayloadContent</key>
    <array>
        <dict>
            <key>IPSec</key>
            <dict>
                <key>AuthenticationMethod</key>
                <string>SharedSecret</string>
                <key>LocalIdentifier</key>
                <string>天行VPN</string>
                <key>SharedSecret</key>
                <string>123456</string>
            </dict>
            <key>IPv4</key>
            <dict>
                <key>OverridePrimary</key>
                <integer>0</integer>
            </dict>
            <key>PPP</key>
            <dict>
                <key>AuthName</key>
                <string>oali29h0001</string>
                <key>AuthPassword</key>
                <string>PZjquAXK</string>
                <key>CCPMPPE40</key>
                <integer>0</integer>
                <key>CCPMPPE56</key>
                <integer>0</integer>
                <key>CCPMPPE128</key>
                <integer>0</integer>
                <key>CommRemoteAddress</key>
                <string>61.172.169.45</string>
                <key>LCPEchoEnabled</key>
                <true/>
                <key>LCPEchoTimeout</key>
                <integer>30</integer>
            </dict>
            <key>PayloadDescription</key>
            <string>天行代理 L2TP/IPSec VPN</string>
            <key>PayloadDisplayName</key>
            <string>天行L2TP</string>
            <key>PayloadIdentifier</key>
            <string>com.tianxing.vpn.l2tp</string>
            <key>PayloadType</key>
            <string>com.apple.l2tp</string>
            <key>PayloadUUID</key>
            <string>${UUID1}</string>
            <key>PayloadVersion</key>
            <integer>1</integer>
            <key>Proxies</key>
            <dict>
                <key>HTTPEnable</key>
                <integer>0</integer>
                <key>HTTPSEnable</key>
                <integer>0</integer>
            </dict>
        </dict>
    </array>
    <key>PayloadDescription</key>
    <string>天行代理 L2TP 自动配置</string>
    <key>PayloadDisplayName</key>
    <string>天行L2TP VPN</string>
    <key>PayloadIdentifier</key>
    <string>com.tianxing.vpn.profile</string>
    <key>PayloadRemovalDisallowed</key>
    <false/>
    <key>PayloadType</key>
    <string>Configuration</string>
    <key>PayloadUUID</key>
    <string>${UUID2}</string>
    <key>PayloadVersion</key>
    <integer>1</integer>
</dict>
</plist>
MOBILECONFIG

echo "✅ .mobileconfig 文件已创建：$PROFILE_PATH"
echo ""
echo "请双击桌面上的「$PROFILE_NAME」文件安装"
echo "安装路径：系统设置 → 通用 → VPN与设备管理 → 安装"
echo "安装后网络里会出现「天行L2TP」VPN"
echo ""
echo "安装完成后，运行下面命令连接测试："
echo "  sudo networksetup -connectpppoeservice \"天行L2TP\""
echo "  sleep 5 && curl -s ifconfig.me"
