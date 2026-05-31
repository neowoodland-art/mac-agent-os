# 本地化适配说明

**基于当前环境的落地调整方案**  
**当前机器**：macOS 26.4，Apple M1，8GB RAM，约 164GB 可用  
**文档日期**：2026-04-27

---

## 一、环境现状扫描结果

| 检查项 | 手册要求 | 当前状态 | 差距 |
|:---|:---|:---|:---|
| **Homebrew** | 用于安装 Colima/Docker | ❌ 未安装 | 需先装 Homebrew |
| **Colima** | 容器运行时 | ❌ 未安装 | 依赖 Homebrew |
| **Docker** | 容器管理 | ❌ 未安装 | 依赖 Homebrew |
| **Python** | 3.10+（脚本运行） | ✅ 3.13.12（managed） | 已满足 |
| **Playwright** | 登录脚本（过渡期） | ✅ 已安装 | 已满足 |
| **Camoufox** | 主力反检测浏览器 | ❌ 未安装 | pip install |
| **Patchright** | 备用反检测浏览器 | ❌ 未安装 | pip install |
| **MLX** | 视觉定位后备 | ❌ 未安装 | pip install |
| **Chrome** | 真实浏览器（CDP 直连） | ❌ 未安装 | 需手动安装 |
| **代理IP** | 每账号独立静态住宅IP | ❌ 未配置 | 需向服务商购买 |
| **账号** | 5-6 个养号账号 | ⚠️ 仅确认1个手机号 | 需补充 |

---

## 二、关键技术路径调整

### 2.1 Docker 方案的现实问题

手册的 Docker + Colima 方案在当前机器上有以下制约：

| 问题 | 说明 | 影响 |
|:---|:---|:---|
| **无 Homebrew** | Colima/Docker 需要 Homebrew 安装 | 安装路径变长 |
| **8GB RAM** | 5个 Docker 容器 + 宿主系统，8GB 会吃紧 | 同时运行容器数有上限 |
| **Camoufox ARM 适配** | Camoufox 的 ARM64 Docker 镜像需要编译，社区还不稳定 | 有编译失败风险 |
| **无 X Display** | macOS Docker 容器跑有头浏览器需要 XQuartz，配置麻烦 | 增加配置难度 |

### 2.2 推荐：分两阶段走

```
阶段 A（现在，1-2周）：CDP 直连本机真实 Chrome
    ↓ 先跑通核心逻辑（登录→养号→蓝图）
阶段 B（稳定后）：切换 Colima + Camoufox/Patchright 容器
    ↓ 上完整反检测方案，扩规模
```

**阶段 A 的优点**：
- 立刻可以开始，不依赖 Docker/Brew
- 真实 Chrome 无指纹问题
- 人工登录流程最自然（你直接在 Chrome 里操作）

**阶段 A 的限制**：
- Chrome 指纹是真实的（反检测弱），适合初期少量账号
- 每次只能跑 1 个 Chrome 实例（不支持多账号并发）

---

## 三、阶段 A：CDP 直连 Chrome 方案（当前可立即执行）

### 3.1 整体架构

```
你的 Mac（本机）
    │
    ├── Chrome 实例 1（账号A）
    │       ├── 调试端口 9222
    │       └── 独立 User Data Dir：~/matrix/profiles/account_01/
    │
    ├── Chrome 实例 2（账号B）
    │       ├── 调试端口 9223
    │       └── 独立 User Data Dir：~/matrix/profiles/account_02/
    │
    └── Python 调度器
            └── 通过 CDP connect_over_cdp() 连接各 Chrome 实例
```

### 3.2 安装步骤（顺序执行）

```bash
# Step 1: 安装 Chrome
# 从 https://www.google.com/chrome/ 下载，安装到 /Applications/

# Step 2: 安装 Python 依赖
/Users/7kecheng/.workbuddy/binaries/python/versions/3.13.12/bin/python3 \
  -m pip install patchright camoufox aiohttp aiosqlite

# Step 3: 安装 Patchright 浏览器核心
/Users/7kecheng/.workbuddy/binaries/python/versions/3.13.12/bin/python3 \
  -m patchright install chromium

# Step 4: 验证
/Users/7kecheng/.workbuddy/binaries/python/versions/3.13.12/bin/python3 \
  -c "from patchright.sync_api import sync_playwright; print('OK')"
```

### 3.3 启动 Chrome 的标准脚本

创建 `~/matrix/scripts/launch_chrome.sh`：

```bash
#!/bin/bash
# 用法: ./launch_chrome.sh <账号ID> <调试端口>
# 示例: ./launch_chrome.sh account_01 9222

ACCOUNT_ID=${1:-account_01}
DEBUG_PORT=${2:-9222}
PROFILE_DIR="$HOME/matrix/profiles/$ACCOUNT_ID"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

mkdir -p "$PROFILE_DIR"

"$CHROME" \
  --remote-debugging-port="$DEBUG_PORT" \
  --user-data-dir="$PROFILE_DIR" \
  --window-size=390,844 \
  --no-first-run \
  --no-default-browser-check \
  --disable-extensions \
  2>/dev/null &

echo "Chrome 已启动，账号: $ACCOUNT_ID，调试端口: $DEBUG_PORT"
echo "验证: curl http://localhost:$DEBUG_PORT/json/version"
```

### 3.4 核心 CDP 连接器

文件：`~/matrix/scripts/cdp_connector.py`

```python
#!/usr/bin/env python3
"""
CDP 连接器 - 连接本机 Chrome 实例
"""
import asyncio
import json
from patchright.async_api import async_playwright

class CDPConnector:
    def __init__(self, port: int = 9222):
        self.port = port
        self.browser = None
        self.context = None
        self.page = None
    
    async def connect(self):
        """连接到已运行的 Chrome"""
        p = await async_playwright().start()
        self.browser = await p.chromium.connect_over_cdp(
            f"http://localhost:{self.port}"
        )
        self.context = self.browser.contexts[0]
        
        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = await self.context.new_page()
        
        print(f"已连接 Chrome（端口 {self.port}），页面数：{len(self.context.pages)}")
        return self.page
    
    async def new_page(self):
        """新建标签页"""
        self.page = await self.context.new_page()
        return self.page
    
    async def goto(self, url: str, wait_until: str = "networkidle"):
        """导航到 URL"""
        await self.page.goto(url, wait_until=wait_until, timeout=30000)
        return self.page
    
    async def setup_anti_jump(self):
        """设置 App 跳转拦截"""
        cdp = await self.context.new_cdp_session(self.page)
        
        blocked_schemes = [
            "xhdsdiscover://*", "snssdk1128://*", "snssdk1233://*",
            "kuaishou://*", "zhihu://*", "weixin://*",
            "alipays://*", "taobao://*", "intent://*",
        ]
        
        await cdp.send("Fetch.enable", {
            "patterns": [
                {"urlPattern": s, "requestStage": "Request"}
                for s in blocked_schemes
            ]
        })
        
        async def handle_paused(event):
            try:
                await cdp.send("Fetch.failRequest", {
                    "requestId": event["requestId"],
                    "errorReason": "Aborted"
                })
            except:
                pass
        
        cdp.on("Fetch.requestPaused", handle_paused)
        return cdp
    
    async def setup_mobile_viewport(self, cdp_session):
        """设置移动端视口（iPhone 15 Pro）"""
        await cdp_session.send("Emulation.setDeviceMetricsOverride", {
            "width": 390, "height": 844,
            "deviceScaleFactor": 3, "mobile": True,
            "screenOrientation": {"type": "portrait", "angle": 0}
        })
        await cdp_session.send("Emulation.setTouchEmulationOverride", {
            "enabled": True, "maxTouchPoints": 5
        })
    
    async def remove_overlays(self):
        """清理 App 跳转弹窗"""
        script = """
        () => {
            const selectors = [
                '[class*="download"]','[class*="open-app"]','[class*="app-guide"]',
                '.open-in-app','.app-launch-mask','.download-tip','.bottom-bar',
                '.download-banner','.open-app-btn','.app-download-tip',
                '.open-app-layer','.download-guide-mask',
                '.open-in-app-bar','.app-open-button',
                '#app-launch-dialog','#open-app-modal',
            ];
            let count = 0;
            selectors.forEach(s => {
                document.querySelectorAll(s).forEach(el => { el.remove(); count++; });
            });
            document.body.style.overflow = '';
            document.body.style.overflowY = 'auto';
            return count;
        }
        """
        removed = await self.page.evaluate(script)
        if removed > 0:
            print(f"  已清理 {removed} 个弹窗/遮罩")
        return removed


# 使用示例
async def main():
    conn = CDPConnector(port=9222)
    page = await conn.connect()
    cdp = await conn.setup_anti_jump()
    await conn.setup_mobile_viewport(cdp)
    
    await page.goto("https://www.douyin.com")
    await asyncio.sleep(2)
    await conn.remove_overlays()
    
    print("当前URL:", page.url)
    print("页面标题:", await page.title())

if __name__ == "__main__":
    asyncio.run(main())
```

### 3.5 登录流程（阶段 A）

```
1. 运行 launch_chrome.sh account_01 9222
2. Chrome 弹出（390×844 手机比例）
3. 你在 Chrome 里手动导航到各平台，手机号登录
4. 登录成功后，Cookie 自动保存在 ~/matrix/profiles/account_01/
5. 关闭 Chrome 窗口
6. 下次用同一个 profile_dir 启动，Cookie 自动复用
```

### 3.6 阶段 A 的内存估算

| 组件 | 内存占用 |
|:---|:---|
| macOS 系统 | ~3GB |
| Chrome 实例 × 2（同时跑） | ~1.5GB × 2 = 3GB |
| Python 调度器 | ~200MB |
| **总计** | **~6.2GB（8GB 机器刚好可以跑 2 个实例）** |

**结论**：阶段 A 最多同时运行 2 个账号，轮换操作其他账号。

---

## 四、阶段 B：Colima + 容器方案（扩展期）

### 4.1 安装 Homebrew（先决条件）

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Apple Silicon 需要添加到 PATH
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

### 4.2 安装 Colima + Docker

```bash
brew install colima docker docker-compose

# 启动（给足资源，8GB 机器建议 6GB 给 Colima）
colima start --cpu 3 --memory 6 --disk 50 --arch aarch64 --vm-type vz

# 验证
docker ps
```

### 4.3 8GB 机器的容器资源分配建议

| 资源 | Colima VM | 宿主系统（macOS） |
|:---|:---|:---|
| CPU | 3核 | 1核（低负载） |
| 内存 | 6GB | 2GB（保底） |
| 磁盘 | 50GB | 剩余 |

**每容器内存限制**（避免 OOM）：

```yaml
# docker-compose.yml 加上限制
services:
  account_01:
    mem_limit: 1.5g
    memswap_limit: 2g
```

**8GB 机器最多稳定运行 3 个容器**（3 × 1.5GB = 4.5GB，留 1.5GB 给系统开销）

### 4.4 Camoufox ARM64 适配

Camoufox 官方 Docker 镜像以 x86 为主，ARM 需要特殊处理：

```dockerfile
# 使用官方提供的 ARM 兼容镜像（如有），或者用 x86 + Rosetta 模拟
FROM --platform=linux/amd64 ubuntu:22.04
```

在 colima 启动时加 Rosetta：
```bash
colima start --cpu 3 --memory 6 --disk 50 --arch x86_64 --vm-type vz --vz-rosetta
```

> **注意**：Rosetta 模拟会有约 20-30% 的性能损耗，但换来更好的兼容性。

---

## 五、现在可以立即做的事（今天）

按优先级排序：

### P0：安装 Chrome（5 分钟）
从 [google.com/chrome](https://www.google.com/chrome/) 下载，安装到 `/Applications/`

### P1：测试 CDP 连接（30 分钟）

```bash
# 启动 Chrome（带调试端口）
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/matrix/profiles/test" \
  --window-size=390,844 &

# 验证 CDP 可用
curl http://localhost:9222/json/version

# 运行连接测试
/Users/7kecheng/.workbuddy/binaries/python/versions/3.13.12/bin/python3 \
  ~/matrix/scripts/cdp_connector.py
```

### P2：登录第一个账号（1 小时）

```bash
# 启动账号 account_01 的 Chrome
bash ~/matrix/scripts/launch_chrome.sh account_01 9222

# 在弹出的 Chrome 里手动登录抖音（手机号 18513308610）
# 成功后关闭 Chrome

# 重新启动，验证 Cookie 是否持久化
bash ~/matrix/scripts/launch_chrome.sh account_01 9222
# 直接打开 https://www.douyin.com，看是否还在登录态
```

### P3：安装 Homebrew（背景任务，不紧急）

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

---

## 六、与手册原文的差异对照表

| 手册原文 | 本地适配版本 | 原因 |
|:---|:---|:---|
| Docker + Colima（全程） | 阶段 A 用原生 Chrome + CDP | 优先跑通核心逻辑，降低初期复杂度 |
| Camoufox 容器 | 阶段 A 用真实 Chrome（指纹原生） | ARM Docker 兼容性风险 |
| 5容器并发 | 阶段 A 最多 2 个账号并发 | 8GB 内存限制 |
| 视口 390×844（容器内） | `--window-size=390,844` 启动参数 | Chrome 直接支持 |
| MLX 本地视觉（同步部署） | 阶段 B 再集成 | 优先走通主流程，MLX 是兜底方案 |

---

## 七、文件清单

```
~/matrix/
├── docs/
│   ├── IMPLEMENTATION_GUIDE.md   ✅ 已创建（完整落地手册）
│   └── LOCAL_ADAPTATION.md       ✅ 本文件
├── scripts/
│   ├── launch_chrome.sh          ← 待创建（Chrome 启动脚本）
│   ├── cdp_connector.py          ← 待创建（CDP 连接器）
│   ├── blueprint_engine.py       ← 待创建（蓝图回放引擎）
│   ├── anti_jump.py              ← 待创建（防跳转模块）
│   └── scheduler.py              ← 待创建（总调度器）
├── profiles/                     ✅ 已创建（账号 Cookie 目录）
├── data/matrix.db                ← 待创建（首次运行自动建）
├── blueprints/                   ✅ 已创建
├── corpus/                       ✅ 已创建
└── docker-compose.yml            ← 阶段 B 再写
```
