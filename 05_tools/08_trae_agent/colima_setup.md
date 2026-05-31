# Colima 沙箱环境配置

**路径**: `05_tools/08_trae_agent/colima_setup.md`
**最后更新**: 2026-05-02

## 概述

trae-agent 默认使用 Docker 容器进行环境隔离。本机通过 Colima（轻量容器运行时）提供 Docker 环境。

## 已安装组件

| 组件 | 版本 | 路径 |
|------|------|------|
| Colima | v0.10.1 | `~/.local/bin/colima` |
| Docker CLI | v29.4.2 | `~/.local/bin/docker` |
| Lima | v2.1.1 | `~/.local/bin/limactl` |
| VM 镜像 | - | `~/.colima/ubuntu-24.04-minimal-cloudimg-arm64-docker.qcow2` |

## 启动 Colima

```bash
# 首次启动
colima start --cpu 2 --memory 4 --disk 20

# 查看状态
colima status

# 停止
colima stop

# 重启
colima restart
```

## 验证 Docker

```bash
# 验证 Docker 是否可用
docker info

# 运行测试
docker run hello-world
```

## 与 trae-agent 集成

```bash
# 默认使用 Docker 隔离
trae_agent.sh run "任务描述"

# 如需跳过 Docker
trae_agent.sh run --no-docker "任务描述"
```

## 常见问题

### Colima 启动失败 - guest agent 找不到
```bash
# 确保 guest agent 文件在正确位置
ls ~/.local/share/lima/lima-guestagent.Linux-aarch64.gz
# 如果缺失:
cp ~/.lima/lima-guestagent.Linux-aarch64.gz ~/.local/share/lima/
```

### Colima 启动失败 - VM 镜像下载慢
```bash
# 手动下载镜像放到 ~/.colima/ 目录
# 启动时指定本地镜像
colima start --disk-image ~/.colima/ubuntu-24.04-minimal-cloudimg-arm64-docker.qcow2
```

### Docker 命令找不到
```bash
export PATH="$HOME/.local/bin:$PATH"
```
