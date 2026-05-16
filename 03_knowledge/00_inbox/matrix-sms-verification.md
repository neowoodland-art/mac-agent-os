---
title: "Matrix 养号系统 SMS 验证码自动接收"
source_dir: 03_knowledge/40_references
source_file: matrix-sms-verification.md
date: 2026-05-11
collected_date: 2026-05-11
tags: [SMS, 验证码, 抖音养号, 自动化登录]
nature: reference
domain: 效率
status: inbox
---

# Matrix 养号系统 SMS 验证码自动接收

> 来源：03_knowledge/40_references

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
ApiSMSH

...（内容已截断，完整内容见源文件）
