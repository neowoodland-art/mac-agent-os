"""
mc — Matrix Console 统一命令入口 v1.0

用法:
  mc run --accounts A,B --blueprints X,Y --rounds 10 --mix
  mc account list
  mc account login <name>
  mc blueprint list
  mc corpus list
  mc proxy list
  mc sms config
  mc status all

设计原则:
  - 所有操作 = 参数 + CLI 命令 + 输出日志
  - 看板是 CLI 的可视化外壳
  - 自动化/Guardd 也只调 CLI
  - 可预测、可重复、可脚本化
"""
__version__ = "1.0.0"
