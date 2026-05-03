---
id: method-20260501-auth-manager
title: 原子化登录管理模块 auth_manager
type: method
tags: [登录检测, Cookie管理, 自动化, matrix]
collected_by: Redmi-12C
created: 2026-05-01
confidence: 0.9
nature: fact

collected: true
collected_date: 2026-05-03---

# auth_manager — 原子化登录管理模块

## 概述
登录检测、Cookie 导出/注入的原子化可复用模块。所有脚本通过此模块统一调用，不再重复写登录检测代码。

## 核心函数

### Cookie 检测（主方案）
```python
check_login_by_cookie(context) → bool  # sessionid/sid_guard 检测
get_session_id(cookies) → str/None      # 提取 sessionid
count_douyin_cookies(cookies) → int     # 统计 douyin Cookie 数量
```

### DOM 检测（备选，仅移动端视口有效）
```python
check_login_by_dom(page, platform) → bool  # 需要 mobile=True 视口
```

### 综合检测
```python
get_login_status(context, page) → dict
# 返回: logged_in, cookie_ok, dom_ok, cookie_count, session_id, method
```

### Cookie 持久化
```python
export_cookies(context, path) → int     # 导出到 JSON 文件
inject_cookies(context, path) → int     # 从 JSON 文件注入
```

### 等待手动登录
```python
wait_for_login(context, page, timeout=300) → dict  # 轮询检测
```

## 设计原则
1. Cookie 检测为主方案（不依赖 UI 布局，桌面端/移动端均可用）
2. DOM 检测为备选（仅在 mobile=True 视口下有效）
3. 所有函数无副作用（不写 DB/文件，除非函数名明确）
4. 统一异常处理（所有异常返回 False/空值）

## 解决的问题
- `switch_account.py` 此前用 `[data-e2e="user-avatar"]` DOM 检测，桌面端视口下该元素不可见，导致已登录账号误报"未登录"
- 所有脚本各自实现登录检测，逻辑分散

## 位置
`05_tools/07_matrix/scripts/auth_manager.py`
