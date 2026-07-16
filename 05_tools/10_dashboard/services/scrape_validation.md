# 内容抓取系统 — 全链路验证方案 v1

> 日期：2026-07-16 | 状态：验证计划
> 覆盖：scrape_db.py → scrape_engine.py → routes/scrape.py → 前端 views/scrape.js

## 测试目标

确保内容抓取系统能端到端工作：从前端输入 sec_uid/URL → 后端适配器采集 → SQLite 存储 → 前端展示结果。

---

## Level 0：基础设施验证（3 项）

### L0-1 ✅ Python import 全链路
```bash
cd ~/workbuddy-agent-os/agent-sync/05_tools/10_dashboard

~/.workbuddy/binaries/python/envs/agent-os/bin/python3 -c "
from services.scrape_db import ScrapeDB
from services.scrape_engine import ScrapeEngine
from services.adapters import ScrapeAdapter
from services.adapters.douyin_scrape import DouyinScrapeAdapter
from services.adapters.browser_helpers import page_evaluate
from routes.scrape import router
from plugins.crawl import CrawlDashboardPlugin
print('✅ All imports OK')
"
```

预期：无 ModuleNotFoundError / ImportError

### L0-2 ✅ SQLite 数据库创建
```bash
~/.workbuddy/binaries/python/envs/agent-os/bin/python3 -c "
from services.scrape_db import ScrapeDB
db = ScrapeDB()
print(f'db_path: {db.db_path}')
tables = db.list_tasks()
print(f'Tables initialized OK, query returned {len(tables)} rows')
"
```
预期：数据库文件 `agent-local/data/scrape.db` 创建成功，4 张表唯美创建

### L0-3 ✅ FastAPI 路由注册
```bash
~/.workbuddy/binaries/python/envs/agent-os/bin/python3 -c "
from routes.scrape import router
routes = [r.path for r in router.routes]
for r in routes: print(f'  {r}')
"
```
预期：看到 `/api/scrape/run`、`/api/scrape/resolve`、`/api/scrape/tasks`、`/api/scrape/items`、`/api/scrape/stats`、`/api/scrape/sources` 等端点

---

## Level 1：数据库层（3 项）

### L1-1 创建任务 + 查任务
```python
db = ScrapeDB()
task_id = db.create_task(type='single', platform='douyin', target='test_url',
                          depth='light', tool_level=2, machine='local', total_targets=1)
task = db.get_task(task_id)
assert task['status'] == 'pending'
assert task['target'] == 'test_url'
print(f'✅ Task #{task_id} created: {task}')
```

### L1-2 写入内容 + 去重
```python
item_id = db.insert_item(task_id=task_id, platform='douyin', item_id='video_001',
                          url='https://douyin.com/video/1', title='测试视频',
                          author_name='测试作者', stats={'likes': 100, 'comments': 5})
assert item_id > 0
# 写入相同 item_id → IGNORE（去重）
item_id2 = db.insert_item(task_id=task_id, platform='douyin', item_id='video_001',
                           title='should be ignored')
assert db.item_exists('douyin', 'video_001') == True
print(f'✅ Item written, dedup works')
```

### L1-3 评论入库 + 查评论
```python
comments = [{'author': '用户A', 'text': '好！', 'likes': 10}]
db.insert_comments(item_db_id=item_id, comments=comments)
got = db.get_comments(item_db_id=item_id)
assert len(got) == 1
assert got[0]['author_name'] == '用户A'
print(f'✅ Comments work: {got}')
```

---

## Level 2：适配器层 — Mock 测试（3 项）

### L2-1 工具降级逻辑
```python
# Mock _try_tools: 模拟 OpenCLI 返回数据
class MockAdapter(ScrapeAdapter):
    platform = 'test'
    adapter_name = 'test_scrape'
    
    async def collect_user(self, uid, limit=20):
        ok, data, tool = await self._try_tools(tool_level=2, funcs=[
            ('opencli', lambda: self._mock_success(uid)),
            ('browser', lambda: self._mock_success(uid)),
        ])
        return data if ok else None
    
    async def _mock_success(self, uid):
        return [{'item_id': 'mock_1', 'title': f'Mock video for {uid}'}]
adapter = MockAdapter()
result = await adapter.collect_user('user_001')
assert len(result) == 1
assert result[0]['item_id'] == 'mock_1'
```

### L2-2 工具降级：一级失败，二级成功
```python
class FallbackAdapter(ScrapeAdapter):
    platform = 'test'
    adapter_name = 'test_fallback'
    async def collect_user(self, uid, limit=20):
        ok, data, tool = await self._try_tools(tool_level=2, funcs=[
            ('opencli', lambda: self._mock_fail('opencli died')),
            ('browser', lambda: self._mock_success(uid)),
        ])
        return (ok, data, tool)
    async def _mock_fail(self, msg):
        raise RuntimeError(msg)
    async def _mock_success(self, uid):
        return [{'item_id': 'fallback_1'}]
adapter = FallbackAdapter()
ok, data, tool = await adapter.collect_user('x')
assert ok and tool == 'browser'
```

### L2-3 统一 Schema 输出
确保各适配器输出的 `collect_item()` 返回的 dict 包含以下字段（无论平台）：
```python
required_keys = ['platform', 'item_id', 'url', 'title', 'author_name',
                  'author_id', 'published_at', 'text_content', 'tags',
                  'stats', 'extra', 'media', 'comments']
```

---

## Level 3：适配器层 — 真实 OpenCLI 验证（3 项）

> 需要 OpenCLI 已安装 + 抖音/小红书 Chrome 已登录

### L3-1 抖音用户视频采集
```python
from services.adapters.douyin_scrape import DouyinScrapeAdapter
adapter = DouyinScrapeAdapter()
items = await adapter.collect_user('r606391422378804368')  # 或任意有公开视频的 sec_uid
assert items, '没有采集到内容'
assert len(items) >= 1
print(f'🎵 抖音采集: {len(items)} 条')
print(f'  第1条: {items[0].get("title","?")} (👍 {items[0].get("stats",{}).get("likes","?")})')
```

### L3-2 小红书用户笔记采集
```python
from services.adapters.xhs_scrape import XhsScrapeAdapter
adapter = XhsScrapeAdapter()
items = await adapter.collect_user('xxx')  # 替换为真实 sec_uid
assert items, '没有采集到内容'
print(f'📕 小红书采集: {len(items)} 条')
```

### L3-3 视频/笔记详情采集
```python
item = await adapter.collect_item('https://www.douyin.com/video/xxx')
assert item.get('title'), '详情采集失败'
assert item.get('comments'), '评论采集失败'
print(f'✅ 详情+评论: {len(item.get("comments",[]))} 条评论')
```

---

## Level 4：引擎层 — ScrapeEngine（3 项）

### L4-1 解析 URL
```python
engine = ScrapeEngine()
results = await engine.resolve_targets([
    'https://www.douyin.com/video/7660182459061436145',
    'https://v.douyin.com/wTknxmL_tgc/',
    'r606391422378804368',  # sec_uid
])
for r in results:
    print(f'  {r.status}: {r.platform}/{r.type} → {r.target_id}')
```

### L4-2 执行单次采集（完整链路）
```python
engine = ScrapeEngine()
targets = [{'input': 'r606391422378804368', 'platform': 'douyin', 'type': 'user', 'target_id': 'r606391422378804368'}]
task_id = engine._create_task('batch', targets, depth='light', tool_level=2)
items = await engine._collect_batch(task_id, targets)
print(f'  {len(items)} 条采集结果')
for item in items:
    print(f'  ✅ {item.get("title","?")} (👍 {item.get("stats",{}).get("likes","?")})')
```

### L4-3 异步任务轮询
```python
# 创建异步任务
result = await engine.run(targets=['r606391422378804368'], async_mode=True)
assert result['status'] == 'async'
run_id = result['run_id']
# 轮询
import time
for i in range(5):
    time.sleep(2)
    status = await engine.get_result(run_id)
    if status['status'] == 'completed':
        break
assert status['status'] == 'completed'
```

---

## Level 5：API 层 — HTTP 端点（4 项）

> 需要 Dashboard 运行中（port 9988）

### L5-1 POST /api/scrape/resolve
```bash
curl -s -X POST http://localhost:9988/api/scrape/resolve \
  -H 'Content-Type: application/json' \
  -d '{"targets":["r606391422378804368","https://www.douyin.com/video/7660182459061436145"]}' \
  | python3 -m json.tool
```
预期：返回目标列表，status 为 resolved

### L5-2 POST /api/scrape/run（同步）
```bash
curl -s -X POST http://localhost:9988/api/scrape/run \
  -H 'Content-Type: application/json' \
  -d '{"targets":["r606391422378804368"],"tool_level":1,"async_mode":false}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'status={d.get(\"status\")}, items={len(d.get(\"data\",[]))}')"
```
预期：同步返回采集结果

### L5-3 GET /api/scrape/items
```bash
curl -s http://localhost:9988/api/scrape/items | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d.get(\"data\",[]))} items')"
```
预期：返回数据库中的采集内容列表

### L5-4 GET /api/scrape/stats
```bash
curl -s http://localhost:9988/api/scrape/stats | python3 -m json.tool
```
预期：{total: N, today: N, sources: N}

---

## Level 6：前端 — UI 验证（4 项）

> 需要打开浏览器访问 http://localhost:9988

### L6-1 导航栏显示
- [ ] 侧边栏导航中看到「内容抓取」入口
- [ ] 点击后跳转到抓取页面
- [ ] 页面顶部显示三个 Tab：新建采集 / 采集源 / 历史

### L6-2 新建采集流程
- [ ] 输入 sec_uid，点击执行
- [ ] 日志区显示进度和结果
- [ ] 结果区展示表格（# / 标题 / 作者 / 点赞 / 评论 / 发布时间）
- [ ] 批量导入多个 URL 可以正常解析

### L6-3 采集源管理
- [ ] 添加采集源成功
- [ ] 采集源列表展示
- [ ] 删除采集源成功

### L6-4 历史记录
- [ ] 历史页面展示任务列表（时间 / 类型 / 目标 / 状态 / 结果数）
- [ ] 点开后能看到详细结果

---

## Level 7：边界与异常（4 项）

### L7-1 OpenCLI 不可用
当 OpenCLI 未安装或不可用时，引擎应该：
- 抛出清晰的错误信息提示安装 OpenCLI
- 如果 tool_level=2，自动降级到浏览器提取
- 日志记录具体失败原因

### L7-2 不支持的平台
```python
engine = ScrapeEngine()
result = await engine._collect_one({'input':'test','type':'user','target_id':'test'}, platform='unknown')
assert result is None
```

### L7-3 空目标列表
```python
result = await engine.run(targets=[])
assert result['status'] == 'error'
```

### L7-4 数据库写入失败
当 SQLite 磁盘满或权限不足时，应返回错误而非崩溃
```python
# 用只读模式创建 DB
import tempfile
db = ScrapeDB('/dev/null')  # 预期：报错而非崩溃
```
