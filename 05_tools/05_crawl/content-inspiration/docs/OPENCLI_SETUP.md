# OpenCLI 集成说明

> 最后更新：2026-06-27

## 用途

通过 Chrome 扩展桥接，实现各平台搜索（抖音/知乎/小红书/B站/微博等）。

## 安装（每台新机器）

```bash
bash install_opencli_extension.sh
```

然后手动：Chrome → chrome://extensions/ → 开发者模式 → 加载已解包 → 选 ~/opencli-extension/

## 验证

```bash
opencli doctor
# [OK] Daemon + [OK] Extension: connected + [OK] Connectivity
```

## 平台登录要求

| 平台 | 需要登录？ |
|------|-----------|
| 百度 | ❌ 不需要 |
| B站 | ✅ 搜索需要登录 |
| 知乎/抖音/小红书/微博 | ✅ 需要登录 |

## 注意事项

- 每台机器各自安装，各自登录
- 重启电脑后需重新启动 daemon

## 本机配置

- 扩展连接码: `9zdft8vm`（随机生成，各机不同）
- Chrome 已登录平台: 百度、B站、知乎、小红书、抖音、微博
- OpenCLI v1.7.21 + 扩展 v1.0.15
- 可用升级: `npm install -g @jackwener/opencli`（到 v1.8.4）+ 扩展 v1.0.20
