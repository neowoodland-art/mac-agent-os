# AgentOS 自动化配置

此目录包含系统定时任务的权威配置，确保自动化配置可恢复。

## 文件说明

| 文件 | 说明 |
|:-----|:------|
| workflows.yaml | WorkBuddy 自动化任务定义（4 个任务） |
| launchd/ | launchd plist 模板（使用 `__PLACEHOLDER__` 替代本机路径） |

## 部署方式

- **WorkBuddy 自动化**: 使用 `agentos init` 或 `agentos sync` 从 workflows.yaml 注册
- **launchd 服务**: 使用 `install_guardd.sh` 自动从模板生成 plist

## 3 个 launchd 服务

| 服务 | plist 模板 | 端口/周期 |
|:-----|:-----------|:----------|
| guardd | com.agentos.guardd.plist.template | 300 秒周期 |
| dashboard | （内嵌在 05_tools/10_dashboard/app.py 启动脚本中） | 9988 端口 |
| socks5-forwarder | （内嵌在 05_crawl/longcat/socks5_forwarder.py 中） | 10800 端口 |
