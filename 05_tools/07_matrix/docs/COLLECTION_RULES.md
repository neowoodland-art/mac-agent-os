# 主页信息采集规则 (Collect Batch Runner)

> 适用于所有机器，联邦统一规则。
> 脚本路径: `~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts/collect_batch_runner.py`

---

## 核心规则

### 1. 最大并发浏览器数: 3

同一时间最多打开 3 个 Camoufox (Firefox) 浏览器窗口。超过会卡顿。

### 2. 启动间隔: 15 秒 + 窗口错位

同一批次内的 3 个身份，每个间隔 15 秒启动浏览器。避免同时加载导致系统卡顿。
同时窗口位置自动错开，不会互相遮挡：

```
身份0 → 位置 (0, 30)     右上角
身份1 → 位置 (852, 30)   右上角（右边错开）
身份2 → 位置 (0, 863)    左下角
```

```
时间线:
  0s    身份 A 启动浏览器 → 抖音 → 小红书 → 关闭
  15s   身份 B 启动浏览器 → 抖音 → 小红书 → 关闭
  30s   身份 C 启动浏览器 → 抖音 → 小红书 → 关闭
```

### 3. 同身份同浏览器

同一个手机号身份下的两个平台（抖音 + 小红书）使用**同一个浏览器窗口**。浏览器打开后先导航到抖音读取主页，再导航到小红书读取主页，最后关闭。不换浏览器。

```
身份(苏州胃肠小曹) → 打开 1 个浏览器:
  1. 导航到 douyin.com → 读取主页信息
  2. 导航到 xiaohongshu.com → 读取主页信息
  3. 关闭浏览器
```

### 4. 分批执行

11 个身份分 4 批：

| 批次 | 身份数 | 预计耗时 |
|------|--------|----------|
| 第1批 | 3 个   | ~2 分钟  |
| 第2批 | 3 个   | ~2 分钟  |
| 第3批 | 3 个   | ~2 分钟  |
| 第4批 | 2 个   | ~1.5 分钟 |

总计约 8-10 分钟（含浏览器启动、页面加载、间隔时间）。

---

## 数据输出

| 文件 | 说明 |
|------|------|
| `data/homepage_info.json` | 最终结果，含 `collected_at` 时间戳 |
| `data/collect_progress.json` | 实时进度（供 Dashboard 轮询） |
| `screenshots/homepage/` | 每个身份的抖音/小红书截屏 |

### 判断数据新旧

`homepage_info.json` 顶部的 `collected_at` 字段记录了本次采集时间：

```json
{
  "collected_at": "2026-06-14T15:18:01",
  "results": [...]
}
```

Dashboard 中会根据这个时间显示相对时间（"刚刚"、"3小时前"、"1天前"），
绿色 = 刚刚采集 / 黄色 = 超过1天。

---

## 前置条件

1. **oMLX**（如需向量库更新）：localhost:8000 运行中
2. **账号已登录**：Camoufox 持久化 profile 中有 session cookie
3. **Python 环境**：matrix venv（含 chromadb、numpy、playwright）

---

## 手动执行

```bash
cd ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts

# 全部采集（分批并行）
python collect_batch_runner.py

# 采集单个身份（顺序执行）
python collect_homepage_info.py --single 手机号
```
