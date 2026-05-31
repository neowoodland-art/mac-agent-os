# 全自动矩阵养号运维系统 - 完整落地实施手册

**版本**：v2.0  
**适用平台**：抖音、小红书、快手、知乎  
**运行环境**：macOS (Apple Silicon), Colima, Docker  
**最后更新**：2026-04-27

---

## 目录

1. [项目概述与目标](#一项目概述与目标)
2. [第一部分：隐身登录系统](#二第一部分隐身登录系统)
3. [第二部分：智能养号自动化系统](#三第二部分智能养号自动化系统)
4. [第三部分：系统完整工作流](#四第三部分系统完整工作流)
5. [第四部分：落地实施具体步骤](#五第四部分落地实施具体步骤)
6. [第五部分：关键技术栈](#六第五部分关键技术栈)
7. [第六部分：成本估算](#七第六部分成本估算)
8. [附录：常见问题与踩坑记录](#八附录常见问题与踩坑记录)

---

## 一、项目概述与目标

### 1.1 项目定义

在 Mac (Apple Silicon) 上构建一套覆盖**抖音、小红书、快手、知乎**的全自动矩阵养号系统。实现从安全登录、拟人化浏览、智能互动到回复评论的全链路自动化。

### 1.2 核心设计原则

- **高隐蔽性**：从浏览器指纹、网络出口、行为特征三个维度做到不被平台风控识别
- **低成本启动**：核心依赖开源工具，初期月成本控制在 ¥135-600
- **自我进化**：采用"人工示教 → AI学习 → 自动回放"模式，适应平台UI变化
- **人机协同**：登录/验证码环节人工介入，重复性操作用自动化完成

### 1.3 前置条件

- 一台专用 Mac (Apple Silicon)，仅用于养号
- 浏览器前台运行，不使用无头模式 (headless: false)
- 登录、验证码环节人工配合
- 5-6 个初始账号，使用 2-3 套反检测框架轮换
- 每个账号绑定独立静态住宅IP

---

## 二、第一部分：隐身登录系统

### 2.1 架构总览

```
🧠 AI 总调度器 (OpenClaw / Python asyncio)
    │
    ├── Docker 容器 1: Camoufox (Firefox) → 账号A → 独立IP_1
    ├── Docker 容器 2: Camoufox (Firefox) → 账号B → 独立IP_2
    ├── Docker 容器 3: Patchright (Chromium) → 账号C → 独立IP_3
    ├── Docker 容器 4: Patchright (Chromium) → 账号D → 独立IP_4
    └── Docker 容器 5: Camoufox (Firefox) → 账号E → 独立IP_5
```

**轮换策略**：
- 3个账号使用 Camoufox (Firefox内核)
- 2个账号使用 Patchright (Chromium内核)
- 避免所有账号使用同一框架，降低群体特征关联风险

### 2.2 容器运行时选型：Colima

**为什么用 Colima 而不是 Docker Desktop**：
- Colima 是 macOS 上最轻量的容器运行时，基于 Lima
- 默认行为更接近原生 Linux 环境，不挂载 `/.dockerenv` 标志文件
- 资源占用小，适合长时间运行
- 开源免费，无 Docker Desktop 的商用限制

**安装命令**：
```bash
brew install colima docker docker-compose
colima start --cpu 4 --memory 8 --disk 50
```

**验证安装**：
```bash
docker ps
# 应显示空的容器列表，无报错
```

### 2.3 Docker 环境反检测技术清单

以下每一项都是经过验证的对抗手段，**必须全部配置**，缺一不可。

| 序号 | 平台检测手段 | 具体表现 | 风险等级 | 我们的对抗方法 | 具体实现 |
|:---|:---|:---|:---|:---|:---|
| 1 | `/.dockerenv` 文件 | 检查根目录是否存在该标志文件 | ⚠️ 高 | 删除该文件 | Dockerfile: `RUN rm -f /.dockerenv` |
| 2 | `/proc/1/cgroup` 关键词 | 检查cgroup是否包含 "docker" 字符串 | ⚠️ 高 | 挂载伪造的cgroup文件 | `-v /host/proc/1/cgroup:/proc/1/cgroup:ro` |
| 3 | 环境变量 `container=docker` | 检测环境变量中是否包含docker标识 | ⚠️ 中 | 清除环境变量 | Dockerfile: `ENV container=""` |
| 4 | `/etc/machine-id` | 系统唯一标识，虚拟机/Docker有固定值 | ⚠️ 中 | 挂载宿主机真实文件 | `-v /etc/machine-id:/etc/machine-id:ro` |
| 5 | D-Bus 服务缺失 | 真实桌面系统必有的进程间通信服务 | ⚠️ 中 | 安装并启动dbus | `RUN apt-get install -y dbus` |
| 6 | 显卡/WebGL 指纹 | 检查是否含 "llvmpipe" 等软件渲染标识 | ⚠️ 高 | Camoufox自动伪造真实GPU信息 | 由Camoufox在编译层处理 |
| 7 | MAC地址虚拟化 | Docker默认生成 `02:42:xx:xx:xx:xx` 段虚拟MAC | ⚠️ 中 | 挂载宿主机网卡或指定固定MAC | `--mac-address 00:1B:63:84:45:E6` |
| 8 | CPU信息 | `/proc/cpuinfo` 显示虚拟化标识 | ⚠️ 低 | 不做特殊处理，Colima默认较干净 | - |
| 9 | 内存/磁盘大小 | 异常小的内存或磁盘容量 | ⚠️ 低 | 分配合理资源（8G内存，50G磁盘） | colima配置参数 |

**Dockerfile 完整模板**：

```dockerfile
# Camoufox 基础镜像
FROM ubuntu:22.04

# 清除Docker标志文件
RUN rm -f /.dockerenv

# 清除环境变量
ENV container=""

# 安装桌面依赖
RUN apt-get update && apt-get install -y \
    dbus \
    libgtk-3-0 \
    libnotify4 \
    libnss3 \
    libxss1 \
    libxtst6 \
    xdg-utils \
    libatspi2.0-0 \
    libdrm2 \
    libgbm1 \
    libxcb1 \
    libxkbcommon0 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# 启动dbus服务
RUN mkdir -p /var/run/dbus && dbus-daemon --system

# 创建非root用户（真实用户不会用root跑浏览器）
RUN useradd -m -s /bin/bash browser
USER browser
WORKDIR /home/browser

# 安装Camoufox（具体步骤见Camoufox官方文档）
# ...
```

**docker-compose.yml 完整模板**：

```yaml
version: '3.8'

services:
  account_01:
    build:
      context: ./docker/camoufox
      dockerfile: Dockerfile
    container_name: matrix_account_01
    volumes:
      - ./profiles/account_01:/home/browser/.mozilla  # Cookie持久化
      - ./scripts:/home/browser/scripts
      - /etc/machine-id:/etc/machine-id:ro              # 宿主机machine-id
    environment:
      - PROXY_SERVER=socks5://your-proxy-ip-1:1080       # 独立代理IP
      - PROXY_USER=your_username
      - PROXY_PASS=your_password
      - DISPLAY=:99
    mac_address: 00:1B:63:84:45:E1                       # 固定MAC
    ports:
      - "9221:9222"  # CDP调试端口，每个容器映射到宿主机不同端口
    shm_size: '2gb'
    restart: unless-stopped

  account_02:
    image: patchright-browser:latest
    container_name: matrix_account_02
    volumes:
      - ./profiles/account_02:/home/browser/.config/chromium
      - ./scripts:/home/browser/scripts
      - /etc/machine-id:/etc/machine-id:ro
    environment:
      - PROXY_SERVER=socks5://your-proxy-ip-2:1080
      - DISPLAY=:99
    mac_address: 00:1B:63:84:45:E2
    ports:
      - "9222:9222"
    shm_size: '2gb'
    restart: unless-stopped

  # account_03, account_04, account_05 类推
```

### 2.4 浏览器层反检测框架详解

#### 2.4.1 Camoufox (Firefox内核)

**为什么选择Camoufox**：
- 在**编译阶段**修改Firefox源码，不是运行时打补丁
- 从根源消除 `navigator.webdriver` 等自动化特征
- WebGL/Canvas/字体指纹均做真实化随机处理
- 对国际主流平台（TikTok, Instagram等）兼容性好

**Camoufox 编译级修改点**：

| 修改点 | 解决的问题 | 技术细节 |
|:---|:---|:---|
| `navigator.webdriver` | 强制返回 `false` | 在Navigator接口实现层硬编码，JS无法检测 |
| CDP Runtime 泄漏 | 移除调试管道痕迹 | 删除 `--remote-debugging-pipe` 参数 |
| WebGL 指纹 | 伪造真实GPU型号 | 注入Apple M系列GPU指纹 |
| Canvas 指纹 | 每次渲染添加微噪声 | 噪声可配置，默认人类无法察觉 |
| 字体指纹 | 模拟真实系统字体列表 | 内置macOS/Windows字体清单 |
| 时区一致性 | IP代理对应时区自动同步 | 启动时检测IP Geo位置自动设置 |

**使用示例**：
```python
from camoufox import AsyncCamoufox

async with AsyncCamoufox(
    headless=False,
    proxy="socks5://ip:port",
    user_data_dir="./profiles/acc01",
    screen={"width": 390, "height": 844},
    geo={"timezone": "Asia/Shanghai"}
) as browser:
    page = await browser.new_page()
    await page.goto("https://www.douyin.com")
```

#### 2.4.2 Patchright (Chromium内核)

**为什么需要Patchright**：
- 基于Chromium内核，对国内Webkit平台（抖音/小红书）兼容性更好
- 修补CDP协议和JS运行时泄漏
- 与Playwright API兼容，学习成本低

**与Camoufox配合使用**：
- 账号A、B、E → Camoufox (Firefox)
- 账号C、D → Patchright (Chromium)
- **关键**：不要让所有账号使用同一浏览器内核

#### 2.4.3 CDP协议连接方式

```python
import asyncio
from patchright.async_api import async_playwright

async def connect_to_browser(cdp_port: int):
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(
            f"http://localhost:{cdp_port}"
        )
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        return page
```

### 2.5 移动端伪装与强制跳转拦截

#### 2.5.1 三层对抗策略

##### 第一层：伪装成"无App环境的普通移动浏览器"

| 参数 | 设置值 | 目的 |
|:---|:---|:---|
| User-Agent | `Mozilla/5.0 (Linux; Android 10; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36` | 伪装成Android手机Chrome |
| UA关键注意 | **绝对不能**包含 `MicroMessenger`、`douyin`、`xiaohongshu`、`kuaishou` 等App标识 | 避免被识别为App内嵌浏览器 |
| `navigator.standalone` | 通过CDP注入强制返回 `false` | 告诉页面"没有安装PWA" |
| `navigator.platform` | `Linux armv8l` | 与UA保持一致性 |

**注意**：UA中的 `Android` 字样不能省略，部分平台对 `iPhone` UA的跳转更激进。

##### 第二层：CDP拦截URL Scheme跳转（最关键防线）

```python
async def setup_app_jump_interception(cdp_session):
    """拦截所有主流平台的App跳转协议"""
    blocked_schemes = [
        "xhdsdiscover://*",      # 小红书
        "snssdk1128://*",        # 抖音
        "snssdk1233://*",        # TikTok
        "kuaishou://*",          # 快手
        "zhihu://*",             # 知乎
        "weixin://*",            # 微信
        "alipays://*",           # 支付宝
        "taobao://*",            # 淘宝
        "openapp.jdmobile://*",  # 京东
        "intent://*",            # Android Intent
    ]
    
    await cdp_session.send("Fetch.enable", {
        "patterns": [
            {"urlPattern": scheme, "requestStage": "Request"}
            for scheme in blocked_schemes
        ]
    })
    
    def handle_interception(event):
        asyncio.ensure_future(
            cdp_session.send("Fetch.failRequest", {
                "requestId": event["requestId"],
                "errorReason": "Aborted"
            })
        )
    
    cdp_session.on("Fetch.requestPaused", handle_interception)
    return cdp_session
```

##### 第三层：DOM弹窗清理（兜底方案）

```python
REMOVE_OVERLAY_SCRIPT = """
() => {
    const overlay_selectors = [
        '[class*="download"]', '[class*="open-app"]', '[class*="app-guide"]',
        '[class*="launch-app"]', '[class*="open-in-app"]',
        '.open-in-app', '.app-launch-mask', '.download-tip', '.bottom-bar',
        '.download-banner', '.open-app-btn', '.app-download-tip',
        '.open-app-layer', '.download-guide-mask',
        '.open-in-app-bar', '.app-open-button',
        '#app-launch-dialog', '#open-app-modal', '#download-modal',
    ];
    
    let removed_count = 0;
    overlay_selectors.forEach(selector => {
        document.querySelectorAll(selector).forEach(el => {
            el.remove();
            removed_count++;
        });
    });
    
    document.body.style.overflow = '';
    document.body.style.position = '';
    document.body.style.overflowY = 'auto';
    
    return removed_count;
}
"""
```

#### 2.5.2 移动端视口配置

```python
MOBILE_VIEWPORT_CONFIG = {
    "width": 390,
    "height": 844,
    "deviceScaleFactor": 3,
    "isMobile": True,
    "hasTouch": True,
    "screenOrientation": "portrait"
}

async def apply_mobile_viewport(cdp_session):
    await cdp_session.send("Emulation.setDeviceMetricsOverride", {
        "width": 390,
        "height": 844,
        "deviceScaleFactor": 3,
        "mobile": True,
        "screenOrientation": {"type": "portrait", "angle": 0}
    })
    await cdp_session.send("Emulation.setTouchEmulationOverride", {
        "enabled": True,
        "maxTouchPoints": 5
    })
```

### 2.6 IP代理配置

| 代理类型 | 月成本/个 | 稳定度 | 适用场景 |
|:---|:---|:---|:---|
| **静态住宅IP** (推荐) | ¥25-110 | ⭐⭐⭐⭐ | 长期养号，被识别风险最低 |
| 动态住宅IP | ¥15-50 | ⭐⭐⭐ | 批量操作，但IP变化可能触发验证 |
| 数据中心代理 | ¥5-20 | ⭐⭐ | 初期测试，但易被风控识别 |

### 2.7 人工登录与Cookie持久化

```
步骤1：启动容器 + 应用代理
步骤2：浏览器弹出（前台，390x844手机比例）
步骤3：人工输入账号密码 + 验证码 + 勾选"记住我"
步骤4：确认登录成功 → Cookie自动写入挂载卷
步骤5：关闭浏览器 → Cookie持久化保留
步骤6：重启容器，验证持久化是否正常
```

```python
async def check_login_status(page, platform: str):
    """检查账号是否仍处于登录状态"""
    login_indicators = {
        "douyin": "document.querySelector('[data-e2e=\"user-avatar\"]') !== null",
        "xiaohongshu": "document.querySelector('.user-avatar') !== null",
        "kuaishou": "document.querySelector('.user-avatar') !== null",
        "zhihu": "document.querySelector('.AppHeader-profile') !== null",
    }
    js_code = login_indicators.get(platform)
    if not js_code:
        return False
    try:
        return await page.evaluate(js_code)
    except:
        return False
```

---

## 三、第二部分：智能养号自动化系统

### 3.1 核心设计：人工示教 → 任务蓝图 → AI回放

**设计理念**：
- 不编写死板的点击坐标脚本
- 人工操作一次，系统自动学习
- 生成结构化"任务蓝图"，AI据此回放
- 平台UI变化时自我修复，失败时降级处理

### 3.2 原子操作定义

| 原子操作ID | 操作名称 | 描述 | 完成确认 |
|:---|:---|:---|:---|
| `AO_NAV` | 页面导航 | 跳转到指定URL | 目标页面关键元素出现 |
| `AO_CLICK` | 点击元素 | 点击指定按钮/链接 | 期望的页面变化发生 |
| `AO_INPUT` | 输入文本 | 在输入框输入内容 | 输入框内容与预期一致 |
| `AO_SCROLL` | 滑动/滚动 | 上下滑动页面 | 滚动位置发生变化 |
| `AO_SWIPE` | 触摸滑动 | 模拟手指滑动（视频切换） | 内容切换到下一条 |
| `AO_WAIT` | 等待 | 停留浏览一段时间 | 等待时间达标 |
| `AO_SEARCH` | 搜索 | 搜索关键词 | 搜索结果加载 |
| `AO_LIKE` | 点赞 | 点亮爱心/拇指 | 按钮状态变为"已赞" |
| `AO_COLLECT` | 收藏 | 收藏内容 | 按钮状态变为"已收藏" |
| `AO_COMMENT` | 评论 | 发表评论 | 评论出现在评论区 |
| `AO_REPLY` | 回复评论 | 回复他人评论 | 回复内容发送成功 |
| `AO_FOLLOW` | 关注 | 关注用户 | 按钮变为"已关注" |

### 3.3 养号任务清单

#### 抖音任务

| 任务ID | 任务名称 | 涉及原子操作 | 预估耗时 |
|:---|:---|:---|:---|
| `DY_001` | 浏览推荐页 | AO_SWIPE, AO_WAIT | 5-15分钟 |
| `DY_002` | 搜索并浏览 | AO_SEARCH, AO_CLICK, AO_WAIT | 3-8分钟 |
| `DY_003` | 点赞视频 | AO_LIKE | 30秒 |
| `DY_004` | 评论视频 | AO_COMMENT, AO_INPUT | 1-2分钟 |
| `DY_005` | 回复评论 | AO_NAV, AO_CLICK, AO_REPLY | 2分钟 |
| `DY_006` | 关注用户 | AO_FOLLOW | 30秒 |
| `DY_007` | 收藏视频 | AO_COLLECT | 30秒 |
| `DY_008` | 浏览同城 | AO_NAV, AO_SWIPE, AO_WAIT | 5分钟 |
| `DY_009` | 查看主页 | AO_NAV, AO_SCROLL | 2分钟 |

#### 小红书任务

| 任务ID | 任务名称 | 涉及原子操作 | 预估耗时 |
|:---|:---|:---|:---|
| `XHS_001` | 浏览首页推荐 | AO_SCROLL, AO_CLICK, AO_WAIT | 5-15分钟 |
| `XHS_002` | 搜索浏览 | AO_SEARCH, AO_SCROLL, AO_CLICK | 5分钟 |
| `XHS_003` | 点赞笔记 | AO_LIKE | 30秒 |
| `XHS_004` | 收藏笔记 | AO_COLLECT | 30秒 |
| `XHS_005` | 评论笔记 | AO_COMMENT, AO_INPUT | 1-2分钟 |
| `XHS_006` | 关注博主 | AO_FOLLOW | 30秒 |

#### 快手任务

| 任务ID | 任务名称 | 涉及原子操作 |
|:---|:---|:---|
| `KS_001` | 刷推荐视频 | AO_SWIPE, AO_WAIT |
| `KS_002` | 点赞视频 | AO_LIKE |
| `KS_003` | 评论视频 | AO_COMMENT, AO_INPUT |

#### 知乎任务

| 任务ID | 任务名称 | 涉及原子操作 |
|:---|:---|:---|
| `ZH_001` | 浏览推荐 | AO_SCROLL, AO_CLICK, AO_WAIT |
| `ZH_002` | 赞同回答 | AO_LIKE |
| `ZH_003` | 评论问题 | AO_COMMENT, AO_INPUT |
| `ZH_004` | 关注话题 | AO_FOLLOW |

### 3.4 任务蓝图完整数据结构

```json
{
  "task_id": "DY_005",
  "task_name": "抖音_回复评论",
  "platform": "douyin",
  "version": "1.0.0",
  "created_at": "2026-04-27T10:00:00Z",
  "created_by": "human_demo",
  "description": "从抖音个人主页进入消息页，找到评论Tab，回复第一条未回复的评论",
  "estimated_duration_ms": 45000,
  
  "execution_environment": {
    "viewport": {"width": 390, "height": 844},
    "user_agent": "Mozilla/5.0 (Linux; Android 10; Pixel 5)...",
    "touch_enabled": true,
    "blocked_schemes": ["xhdsdiscover://*", "snssdk1128://*"],
    "overlay_removal": true
  },
  
  "steps": [
    {
      "step_id": 1,
      "step_name": "点击消息Tab进入通知页",
      "atomic_operation": "AO_CLICK",
      
      "locator": {
        "primary": "[data-e2e='message-tab']",
        "fallback_xpath": "//div[contains(@class,'tab')]//span[contains(text(),'消息')]",
        "fallback_visual": {
          "text": "消息",
          "description": "底部导航栏的消息图标按钮"
        }
      },
      
      "behavior": {
        "click_mode": "touch",
        "pre_delay_ms": [500, 1200],
        "touch_duration_ms": [50, 100],
        "post_delay_ms": [1500, 2500]
      },
      
      "post_checks": [
        {"type": "url_changed", "expected_pattern": "/notice/*"},
        {"type": "element_appeared", "selector": "[data-e2e='comment-tab']"}
      ],
      
      "on_failure": {"max_retries": 2, "fallback_action": "retry_with_visual"}
    }
  ],
  
  "completion_verification": {
    "success_indicators": [
      {"type": "element_appeared", "selector": "[data-e2e='reply-sent-success']"}
    ],
    "timeout_ms": 60000
  }
}
```

### 3.5 任务蓝图数据库设计

```sql
-- 任务蓝图主表
CREATE TABLE task_blueprints (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    task_name TEXT NOT NULL,
    platform TEXT NOT NULL,
    version TEXT NOT NULL,
    status TEXT DEFAULT 'active',     -- 'active', 'deprecated', 'broken'
    browser_framework TEXT,
    viewport_config TEXT,
    entry_conditions TEXT,
    steps_json TEXT,
    completion_check_json TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    deprecation_reason TEXT,
    replaced_by_version TEXT
);

-- 任务执行记录表
CREATE TABLE task_executions (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    blueprint_version TEXT NOT NULL,
    account_id TEXT NOT NULL,
    browser_framework TEXT,
    container_id TEXT,
    proxy_ip TEXT,
    status TEXT,                      -- 'running', 'success', 'failed', 'timeout'
    started_at TEXT,
    completed_at TEXT,
    duration_ms INTEGER,
    error_message TEXT,
    screenshots TEXT,
    logs TEXT
);

-- 原子操作执行记录
CREATE TABLE operation_logs (
    id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    step_id INTEGER,
    atomic_operation TEXT,
    pre_checks_passed BOOLEAN,
    execution_success BOOLEAN,
    post_checks_passed BOOLEAN,
    locator_used TEXT,
    duration_ms INTEGER,
    error_detail TEXT,
    screenshot_path TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- UI变更记录
CREATE TABLE ui_changes (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    platform TEXT,
    detected_at TEXT,
    element_changed TEXT,
    old_selector TEXT,
    new_selector TEXT,
    affected_blueprint_versions TEXT,
    resolution TEXT,
    notes TEXT
);
```

### 3.6 三级元素定位策略

```python
class SmartLocator:
    """
    智能元素定位器
    Level 1: 录制的CSS选择器（90%场景）
    Level 2: 备选XPath（8%场景）
    Level 3: 本地MLX视觉定位（2%场景，兜底）
    """
    async def locate_element(self, page, step: dict):
        # Level 1: 首选CSS选择器
        primary = step["locator"]["primary"]
        try:
            element = await page.wait_for_selector(primary, timeout=3000)
            if element:
                return {"level": 1, "element": element}
        except:
            pass
        
        # Level 2: 备选XPath
        fallback_xpath = step["locator"].get("fallback_xpath")
        if fallback_xpath:
            try:
                element = await page.wait_for_selector(f"xpath={fallback_xpath}", timeout=3000)
                if element:
                    return {"level": 2, "element": element}
            except:
                pass
        
        # Level 3: MLX视觉定位
        return await self._visual_locate(page, step)
```

### 3.7 本地MLX多模态后备

```bash
# 安装MLX和视觉模型
pip install mlx mlx-vlm

# 下载量化版视觉模型（Qwen2-VL-7B-4bit，内存占用<5GB）
python -c "
from mlx_vlm import load
model, processor = load('mlx-community/Qwen2-VL-7B-4bit')
"
```

```python
async def mlx_vision_locate(image_bytes: bytes, target_description: str, target_text: str = ""):
    """使用本地MLX模型在截图中定位目标元素"""
    model, processor = get_mlx_model()
    image = Image.open(io.BytesIO(image_bytes))
    
    prompt = f"""在这张手机截图中，找到"{target_description}"的位置。
该元素的文字可能是"{target_text}"。
请返回该元素的外接矩形坐标，格式为：x1,y1,x2,y2
只返回坐标数字，不要包含其他内容。"""
    
    response = generate(model, processor, image=image, prompt=prompt, max_tokens=50)
    
    try:
        parts = response.strip().split(",")
        if len(parts) == 4:
            x1, y1, x2, y2 = map(int, parts)
            return {"x": (x1+x2)//2, "y": (y1+y2)//2, "x1":x1, "y1":y1, "x2":x2, "y2":y2}
    except:
        pass
    return None
```

**MLX方案的优势**：零网络延迟（200-500ms）、零API费用、数据不离本机。

### 3.8 养号行为拟人化参数

```python
class BehaviorProfile:
    def __init__(self, account_id: str, persona: str = "normal"):
        self.params = {
            "action_delay": [200, 5000],       # 动作间隔（毫秒）
            "view_duration": [5000, 60000],    # 浏览停留（毫秒）
            "move_duration": [100, 800],       # 鼠标/触摸移动时间
            "typing_speed": [50, 200],         # 每字符毫秒
            "typo_probability": [0, 0.05],     # 打字错误概率
            "active_hours": [8, 23],           # 每日活跃时段
            "max_likes_per_hour": 20,
            "max_comments_per_hour": 5,
            "max_follows_per_hour": 10,
            "max_total_actions_per_day": 200,
        }
```

---

## 四、第三部分：系统完整工作流

### 4.1 日常运行全景

```
每日启动（定时/手动）
    │
调度器加载排班表，确定今日任务序列
    │
    ├── 启动容器1 + 加载代理
    ├── 启动容器2 + 加载代理
    └── 启动容器3 + 加载代理
    │
    检查Cookie登录状态
    有效 → 直接执行 | 过期 → 通知人工
    │
    各账号执行任务序列（浏览/点赞/评论/关注）
    │
    每个步骤：前置校验 → 执行 → 后置校验
    成功 → 记录日志 → 下一步
    失败 → 降级定位 → 重试 → 人工介入
    │
    冷却10-30分钟
    │
    释放容器，生成今日执行报告
```

### 4.2 账号熔断机制

```python
class CircuitBreaker:
    def __init__(self, account_id: str):
        self.failure_count = 0
        self.max_failures = 3
        self.cooldown_minutes = 30
        self.is_open = False
    
    async def record_failure(self):
        self.failure_count += 1
        if self.failure_count >= self.max_failures:
            self.is_open = True
            await notify_admin(f"账号 {self.account_id} 连续失败已熔断")
    
    def can_execute(self) -> bool:
        if not self.is_open:
            return True
        if time.time() - self.opened_at > self.cooldown_minutes * 60:
            self.is_open = False
            self.failure_count = 0
            return True
        return False
```

---

## 五、第四部分：落地实施具体步骤

### 阶段0：环境准备（预计1-2天）

```bash
brew install colima docker docker-compose
colima start --cpu 4 --memory 8 --disk 50
docker ps  # 验证

pip install asyncio aiohttp playwright patchright camoufox
mkdir -p ~/matrix/{docker/{camoufox,patchright},profiles,scripts,data,logs,screenshots}
```

### 阶段1：隐身容器跑通 + 人工登录（预计2-3天）

- [ ] 编写 Camoufox Dockerfile（含所有反检测配置）
- [ ] 编写 Patchright Dockerfile
- [ ] 编写 docker-compose.yml（5个容器）
- [ ] 准备2个静态住宅IP
- [ ] `docker-compose up account_01` 启动容器，人工登录抖音
- [ ] 验证跳转拦截：小红书网页版是否有弹窗
- [ ] 验证Cookie持久化

**里程碑**：2账号 × 2框架 × 独立IP，同时在线，无跳转弹窗。

### 阶段2：示教录制与蓝图生成（预计3-5天）

- [ ] 编写CDP监听脚本
- [ ] 连接容器，启动示教模式
- [ ] 人工演示"抖音_浏览推荐页 + 点赞"完整流程
- [ ] 验证生成的蓝图JSON结构是否合理
- [ ] 录制3-5个基础任务蓝图，入库SQLite

### 阶段3：蓝图回放验证（预计3-5天）

- [ ] 编写蓝图回放引擎
- [ ] 验证自我修复：故意损坏选择器，观察降级定位
- [ ] 连续3天存活率测试

**里程碑**：AI完成完整浏览+点赞+关注序列，无人工干预，3天内未被风控。

### 阶段4：集成调度器（预计2-3天）

- [ ] asyncio调度器 + 排班表
- [ ] 每日执行报告
- [ ] crontab 定时启动

### 阶段5：扩展任务库与多平台（持续）

- [ ] 小红书/快手/知乎核心蓝图录制
- [ ] 接入 DeepSeek 评论生成
- [ ] 5账号全量跑通，观察1周稳定性

### 阶段6：MLX本地视觉后备（预计1-2天）

- [ ] 安装MLX + 下载 Qwen2-VL-7B-4bit
- [ ] 集成视觉定位为第三级降级
- [ ] 压测定位延迟（目标 < 500ms）

---

## 六、第五部分：关键技术栈总览

| 层级 | 工具 | 用途 | 是否免费 |
|:---|:---|:---|:---|
| 容器运行时 | Colima | 轻量Docker替代 | ✅ |
| 反检测浏览器 | Camoufox | Firefox内核，编译级反检测 | ✅ |
| 反检测浏览器 | Patchright | Chromium内核，修补CDP泄漏 | ✅ |
| CDP通信 | nodriver / patchright | 驱动浏览器 | ✅ |
| 行为模拟 | 自定义触摸模拟 | 拟人化触摸操作 | ✅ |
| IP代理 | 静态住宅代理 | 独立IP出口 | ❌ |
| 任务调度 | Python asyncio | 编排多账号并发 | ✅ |
| AI编排 | OpenClaw (可选) | 自然语言转任务指令 | ✅ |
| 数据库 | SQLite | 存储蓝图和日志 | ✅ |
| 多模态AI | MLX + Qwen2-VL | 本地视觉定位 | ✅ |
| 评论生成 | DeepSeek API | 智能评论内容 | ❌（极低） |

---

## 七、第六部分：成本估算

### 初期5账号方案

| 项目 | 月成本 | 年成本 | 备注 |
|:---|:---|:---|:---|
| 静态住宅IP ×5 | ¥125-550 | ¥1500-6600 | ¥25-110/个/月 |
| 反检测框架 | ¥0 | ¥0 | 开源 |
| MLX本地模型 | ¥0 | ¥0 | 仅消耗电费 |
| 评论API | ¥10-50 | ¥120-600 | DeepSeek按量付费 |
| **月总成本** | **¥135-600** | | |

### 与商业方案对比

| 方案 | 月成本 (5账号) | 灵活性 | 技术门槛 |
|:---|:---|:---|:---|
| **本方案 (开源自建)** | ¥135-600 | ⭐⭐⭐⭐⭐ | 中高 |
| AdsPower + RPA | ¥300-1000+ | ⭐⭐⭐ | 中 |
| 商业群控系统 | ¥1000-5000 | ⭐⭐ | 低 |

---

## 八、附录：常见问题与踩坑记录

### 容器相关

**Q: Docker ps 报错 "permission denied"**
```bash
sudo usermod -aG docker $USER
# 重新登录终端
```

**Q: 容器内浏览器无法启动，报错 "no display"**
```yaml
environment:
  - DISPLAY=host.docker.internal:0
```

### 反检测相关

**Q: 平台仍然检测到WebDriver**
- 确认Camoufox使用最新版本
- 确认没有传入 `--enable-automation` 参数
- 通过CDP覆写 `navigator.webdriver`

**Q: 小红书仍然强制跳转App**
- 检查UA中是否包含小红书App标识
- 确认URL Scheme拦截是否生效
- 尝试增加 `navigator.standalone = false` 覆写

### 蓝图相关

**Q: 录制时选择器不稳定**
- 优先选择 `data-e2e` 等平台埋点属性
- 避免依赖动态生成的class名
- 使用相对位置关系作为备选定位

**Q: MLX视觉定位速度慢**
- 确保使用4bit量化版模型
- 降低截图分辨率（1920→960）
- 先用OCR预筛选，再调用VL模型

---

*此手册整合了完整讨论内容，后续开发过程中如有新问题，随时补充到附录。*
