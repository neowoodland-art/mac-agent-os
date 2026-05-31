---
id: KB-20260510-001
title: "Matrix 养号系统 SMS 验证码自动接收"
type: system
status: active
nature: reference
domain: system
subdomain: [matrix, 养号, 自动化]
tags: [SMS, 验证码, 抖音养号, 自动化登录]
confidence: 0.9
source: "07_matrix 养号系统代码审查"
date_created: 2026-05-10
date_modified: 2026-05-10
version: 1
summary: "SMS 验证码自动接收模块，通过 wx.tyhtak.com API 轮询获取短信验证码，替代手动输入。配置已从源码提取到 config/sms.yaml。"

collected: true
collected_date: 2026-05-16---

# SMS 验证码自动接收模块

## 架构

```
base.py — SMSHandler（抽象基类）
  ├── ManualSMSHandler — 手动输入（信号文件交互）
  └── ApiSMSHandler — API 自动轮询（默认）
       API: https://wx.tyhtak.com/api/biz/msg/messages
       配置: config/sms.yaml
```

## 配置

位置：`config_template/sms.yaml`（模板）→ `scripts/config/sms.yaml`（实际）
每台机器独立，已加入 .gitignore。

```yaml
sms:
  api_key: "gtmsg2026"
  phone: "15370103682"
  base_url: "https://wx.tyhtak.com/api/biz/msg/messages"
  poll_interval: 3
  timeout: 120
```

## 工作流程

```
养号脚本需要验证码
  ↓
ApiSMSHandler.wait() 启动轮询
  ↓ 每3秒拉一次API
检测到新短信 → 提取验证码（4-6位数字）
  ↓
返回给登录流程自动填入
```

## 注意事项

- API Key 和手机号已从源码提取到配置文件，不再硬编码
- 超时120秒，可配置
- API 不可用时会打印警告，不中断流程
