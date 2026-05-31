# Matrix IP 切换方案 — 完整指南

> 更新：2026-04-27 | 针对抖音养号场景的 IP 策略

---

## 一、为什么需要切换 IP？

| 场景 | 不切 IP 的风险 |
|------|----------------|
| 多账号同设备 | 同 IP 登录 3+ 账号 → 关联封号 |
| 高频操作 | 同 IP 点赞/评论 > 阈值 → 触发验证码 |
| 跨地域 | IP 归属地与注册地不一致 → 风控 |

---

## 二、IP 类型对比

| 类型 | 原理 | 检测难度 | 价格 | 适用场景 |
|------|------|---------|------|---------|
| **数据中心 IP** | 服务器出口 IP | ❌ 极易被识别 | ¥0.5-2/个 | 不推荐 |
| **轮转住宅 IP** | 真实家庭宽带，每次请求换 IP | ✅ 难识别 | ¥10-30/GB | 数据采集 |
| **静态住宅 IP** | 真实家庭宽带，IP 固定不变 | ✅✅ 最难识别 | ¥5-15/个/月 | **养号（推荐）** |
| **免费代理** | 公开代理列表 | ❌ 不可靠 | 免费 | ❌ 不推荐 |

### 养号场景的最佳选择：**静态住宅 IP**

原因：
1. **IP 固定** → 同一账号始终同一 IP，不会被抖音识别为"频繁换设备"
2. **真实住宅** → 不会被代理检测库标记
3. **按月付费** → 成本可控，不像流量计费那么贵

---

## 三、服务商对比（2026 年价格）

### 🏆 性价比 TOP 3

| 服务商 | 静态住宅 IP | 最低月费 | 流量限制 | 中国 IP | 推荐指数 |
|--------|-----------|---------|---------|---------|---------|
| **IPFoxy** | ¥5-8/个/月 | ¥30/月起 | 无限流量 | ✅ | ⭐⭐⭐⭐⭐ |
| **巨量HTTP** | ¥3-6/个/月 | ¥20/月起 | 无限流量 | ✅ | ⭐⭐⭐⭐ |
| **Bright Data** | $1.3/个起 | ~¥60/月起 | 按流量 | ✅ | ⭐⭐⭐ |

### 国内服务商（推荐——延迟低、中国 IP 充足）

| 服务商 | 静态住宅 IP | 特点 |
|--------|-----------|------|
| **巨量HTTP** (jlhttp.com) | ¥3-6/个/月 | 国内老牌，IP池大，中文客服 |
| **青果代理** (qg.net) | ¥5-8/个/月 | 专注社交账号，有养号套餐 |
| **站大爷** (zdaye.com) | ¥4-7/个/月 | 支持城市级定位 |
| **IPFoxy** (ipfoxy.io) | ¥5-8/个/月 | 全球覆盖，支持 SOCKS5 |

### 国际服务商（适合海外平台）

| 服务商 | 静态住宅 IP | 特点 |
|--------|-----------|------|
| **Bright Data** | $1.3/个起 | 全球最大 IP 池，4亿+ |
| **Smartproxy** | $2/个起 | 性价比不错 |
| **Oxylabs** | $1.8/个起 | 企业级，稳定性最好 |

### 🆓 免费/低成本方案

| 方案 | 限制 | 可行性 |
|------|------|--------|
| **自建 VPS + 代理** | 需技术，IP 可能被标记 | ⚠️ 中等 |
| **Cloudflare WARP** | 共享 IP，非住宅 | ⚠️ 中等 |
| **公开代理列表** | 极不稳定，秒断 | ❌ 不可行 |
| **手机 4G/5G 热点** | 真实住宅级，但只有 1 个 IP | ✅ 单账号可用 |

---

## 四、推荐方案

### 方案一：最低成本（¥0-30/月）

```
适用：2-3 个账号
方案：手机热点 + 家里宽带

1. 账号1 → 家里 WiFi（固定 IP）
2. 账号2 → 手机 4G 热点（固定 IP）
3. 账号3 → 手机 5G 热点（换 SIM/飞行模式换 IP）

成本：¥0（已有手机卡）
```

### 方案二：性价比（¥30-100/月）⭐ 推荐

```
适用：5-10 个账号
方案：2-3 个静态住宅 IP + Profile 切换

1. 买 2-3 个中国静态住宅 IP（巨量HTTP/IPFoxy）
   - 每个 IP 绑定 2-3 个账号
   - 通过 Chrome Profile 切换账号
2. 代理配置写在 launch_chrome.sh 里

成本：¥30-50/月（5个IP × ¥6-10）
```

### 方案三：专业级（¥200+/月）

```
适用：10-30 个账号
方案：每个账号独立 IP + 自动化调度

1. 每个账号 1 个静态住宅 IP
2. task_scheduler 自动轮换
3. 不同账号不同时段执行

成本：¥150-300/月
```

---

## 五、技术集成方案

### 1. Chrome 启动时注入代理

`launch_chrome.sh` 已支持，只需添加代理参数：

```bash
# HTTP 代理
"$CHROME" \
    --proxy-server="http://user:pass@proxy.example.com:8080" \
    --remote-debugging-port="$DEBUG_PORT" \
    --user-data-dir="$PROFILE_DIR"

# SOCKS5 代理
"$CHROME" \
    --proxy-server="socks5://user:pass@proxy.example.com:1080" \
    --remote-debugging-port="$DEBUG_PORT" \
    --user-data-dir="$PROFILE_DIR"
```

### 2. switch_account.py 集成

账号配置增加 `proxy` 字段：

```yaml
accounts:
  - id: douyin_01
    proxy: "http://user:pass@cn-proxy1.example.com:8080"
  - id: douyin_02
    proxy: "socks5://user:pass@cn-proxy2.example.com:1080"
```

### 3. CDP 代理验证

```python
# 通过 CDP 检查当前出口 IP
import json, urllib.request

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
# 通过浏览器请求 IP 检测
result = await page.evaluate('fetch("https://httpbin.org/ip").then(r=>r.json())')
print(f"当前出口 IP: {result['origin']}")
```

---

## 六、反检测策略矩阵

| 检测维度 | 方案A（Profile 切换） | 方案B（Cookie 注入） |
|---------|---------------------|---------------------|
| **IP** | 每个 Profile 用不同代理 | 切换时换代理 |
| **浏览器指纹** | 真实 Chrome（原生） | 真实 Chrome（原生） |
| **Cookie** | Profile 自带 | 手动注入 |
| **Canvas 指纹** | 每个 Profile 不同（GPU 渲染差异） | 同一 Canvas |
| **WebGL 指纹** | init_script 注入 | init_script 注入 |
| **Audio 指纹** | 每个 Profile 不同 | 同一 |
| **navigator** | webdriver=undefined | webdriver=undefined |
| **时区/语言** | CDP 覆盖 | CDP 覆盖 |

---

## 七、下一步行动

1. ✅ `switch_account.py` 已实现（方案A+B）
2. 📋 买 2-3 个中国静态住宅 IP（推荐 巨量HTTP 或 IPFoxy）
3. 📋 在 `accounts.yaml` 配置代理
4. 📋 `launch_chrome.sh` 增加代理参数
5. 📋 自动化调度：不同账号+不同IP+不同时段

