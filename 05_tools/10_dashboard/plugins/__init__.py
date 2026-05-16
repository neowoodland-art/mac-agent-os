"""
Dashboard 数据源插件系统

架构:
  各模块实现 DashboardPlugin 基类, 在 app.py 启动时自动注册。
  Dashboard 对每个插件调用 get_*() 方法获取数据, 统一返回前端。

注册:
  app.py 在启动时扫描 plugins/ 目录, 加载所有继承 DashboardPlugin 的类。
  通过 PLUGIN_ORDER 控制展示顺序。

用法:
  from plugins.base import DashboardPlugin
  from plugins.ave import AVEDashboardPlugin
  plugins = [AVEDashboardPlugin()]
"""
