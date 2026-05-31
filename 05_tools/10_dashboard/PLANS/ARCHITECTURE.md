# 系统监控面板 (10_dashboard) 架构设计

> 版本: 1.0.0 | 更新: 2026-05-16
> 定位: 系统级监控层, 联邦架构可视化面板

---

## 一、架构总览

```
10_dashboard/                      ← 系统级监控面板
├── app.py                          FastAPI 后端 (插件注册 + API 路由)
├── run.py                          独立启动入口
├── config.yaml                     (预留) 数据源配置
├── static/index.html               前端 SPA
├── plugins/
│   ├── __init__.py                 插件管理器
│   ├── base.py                     DashboardPlugin 基类
│   └── ave.py                      AVE 视频工厂数据源插件
└── PLANS/ARCHITECTURE.md           本文件
```

## 二、数据流

```
┌─────────────────────────────────────────────────┐
│                 用户浏览器 (SPA)                   │
└─────────────────┬──────────────┬────────────────┘
                  │ GET /api/*   │
                  ▼              ▼
┌─────────────────────────────────────────────────┐
│          10_dashboard/app.py (FastAPI)           │
│                                                   │
│  /api/plugins → 插件列表                           │
│  /api/summary → 所有插件聚合总览                    │
│  /api/productions → AVE 插件                       │
│  /api/assets/* → AVE asset_manager                 │
│  /api/costs/* → AVE 插件                           │
└─────────┬──────────────────────┬──────────────────┘
          │                      │
          ▼                      ▼
  ┌──────────────┐    ┌──────────────────┐
  │ AVE 插件      │    │ (未来) Matrix     │
  │ plugins/ave.py│    │ guardd / 其他     │
  │ → AVE DB      │    │ → 各自 DB/API    │
  └──────────────┘    └──────────────────┘
```

**核心原则**:
- 数据不搬家: Dashboard 只读, 不复制数据
- 插件隔离: 每个模块的数据源在自己的 plugin 中处理
- 增量接入: 新模块只需实现 DashboardPlugin 基类

## 三、插件协议

```python
class DashboardPlugin:
    name: str           # "ave", "matrix", "guardd"
    label: str          # "视频工厂", "矩阵养号", "系统状态"
    order: int          # 展示排序

    def get_summary(self) -> dict
    def get_productions(self, limit, offset, strategy, status) -> list
    def get_production_detail(self, id) -> dict|None
    def get_cost_breakdown(self) -> list
    def get_sidebar_links(self) -> list[dict]
    def is_available(self) -> bool
```

## 四、与 AVE 的边界

| 组件 | 归属 | 说明 |
|:-----|:----:|:-----|
| `lib/dashboard.py` | **09_ave** | AVE 数据写入层 (production/step/asset/cost 埋点) |
| `asset_manager/` | **09_ave** | AVE 素材索引 (AssetIndex/CacheManager/AssetSearch) |
| `cost_tracker.py` | **09_ave** | AVE 费用追踪 |
| `plugins/ave.py` | **10_dashboard** | AVE 数据读取适配器 |
| `app.py` | **10_dashboard** | 系统级后端, 加载所有插件 |
| `static/index.html` | **10_dashboard** | 前端 SPA, 模块化展示 |

## 五、接入新模块 (示例: Matrix)

```python
# 10_dashboard/plugins/matrix.py
from plugins.base import DashboardPlugin

class MatrixDashboardPlugin(DashboardPlugin):
    name = "matrix"
    label = "矩阵养号"
    order = 2

    def get_summary(self) -> dict:
        # 读取 matrix.db 返回统计数据
        ...

    def is_available(self) -> bool:
        return Path("~/matrix/data/matrix.db").exists()
```

然后在 `app.py` 的 `_register_plugins()` 中添加 `MatrixDashboardPlugin` 即可。

## 六、启动方式

```bash
# 方式 1: 通过 AVE 入口 (推荐)
cd 09_ave/scripts && python main.py dashboard

# 方式 2: 独立启动
cd 10_dashboard && python run.py

# 方式 3: uvicorn (开发模式)
cd 10_dashboard && uvicorn app:app --reload --port 9988
```

## 七、迁移要点 (Phase 1)

1. ✅ 目录搬移: `dashboard/` → `10_dashboard/`
2. ✅ Import 路径: app.py 通过 `../09_ave/scripts/` 引用 AVE 模块
3. ✅ 插件框架: base.py + ave.py 实现
4. ✅ main.py 入口: dashboard 命令指向新路径
5. ✅ 前端兼容: 旧 API 路径保持不变
6. ⬜ 多机同步: 通过坚果云 / Gitee 同步 10_dashboard/
