# SMS 验证码 API 使用说明

## 服务地址
`https://wx.tyhtak.com`

## API 接口
```
GET /api/biz/msg/messages
  ?api_key=gtmsg2026
  &receiver_phone={phone}
  &page=1&per_page=20
```

## 配置方式

### 1. 全局默认手机号（scripts/config/sms.yaml）
```yaml
sms:
  api_key: "gtmsg2026"
  phone: "15370103682"        # 默认手机号
  base_url: "https://wx.tyhtak.com/api/biz/msg/messages"
```

### 2. 账号级手机号（accounts.yaml）
```yaml
accounts:
  - id: douyin_01
    phone: "18513308610"       # 每个账号绑定自己的手机号
  - id: douyin_02
    phone: "18500003366"
  - id: douyin_camo01
    phone: "15370103682"
```

### 3. 运行时优先级
`sms_login(account_name='douyin_02')` → 查 accounts.yaml → 拿到 phone=18500003366 → 调用 API 时用 `receiver_phone=18500003366`

### 4. 三个账号的 API 支持情况
所有账号共用同一个 API 平台（wx.tyhtak.com），只需在 API URL 中替换 `receiver_phone` 参数即可查询对应手机号的短信。

| 账号 | 手机号 | API receiver_phone |
|------|--------|-------------------|
| douyin_01 | 18513308610 | 替换即可 |
| douyin_02 | 18500003366 | 替换即可 |
| douyin_camo01 | 15370103682 | 替换即可 |

## 使用方式
```python
# 自动模式：从 accounts.yaml 查手机号
from matrix_modules.account.sms_login import sms_login
ok = await sms_login(page, account_name='douyin_02')

# 手动模式：指定手机号
from matrix_modules.account.sms import ApiSMSHandler
handler = ApiSMSHandler(phone='18500003366')
code = await handler.wait('抖音登录', timeout=60)
```
