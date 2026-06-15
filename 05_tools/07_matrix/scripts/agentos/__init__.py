"""
AgentOS — 联邦智能体统一命令入口

命名空间:
  agentos matrix     社交矩阵（抖音/小红书运营）
  agentos ave        视频工厂（视频制作与编辑）
  agentos crawl      内容采集（互联网内容抓取）
  agentos fleet      联邦管理（多机协同）
  agentos serve      服务管理（MCP/Dashboard/调度）

用法:
  agentos matrix run --accounts A,B --blueprints X,Y
  agentos fleet sync
  agentos serve mcp
  agentos --help

设计原则:
  - 每个领域是一个插件，放在 plugins/ 目录下
  - 插件自动发现，加领域 = 加文件
  - 所有操作可远程执行 (--on 指定目标机器)
  - 所有操作支持 --json 输出
"""
__version__ = "0.1.0"
