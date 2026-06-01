# 7kecheng → chengzigedeAir SSH 配置

> 最后更新：2026-06-01 20:15

## 连接信息

| 项目 | 值 |
|------|-----|
| 主机 | chengzigedeAir |
| IP | 192.168.31.101 |
| 端口 | 22 |
| 用户 | chengzige |
| 密钥 | `id_ed25519_chengzigedeAir` |

## 7kecheng 上执行

### 方式一：通过 Git 仓库获取私钥

本机私钥文件路径: `~/.ssh/id_ed25519_7kecheng`，需要通过安全通道传递给 7kecheng。

### 方式二：手动复制

在 7kecheng 上创建一个新的 SSH 密钥对，然后把公钥发过来：

```bash
# 在 7kecheng 上生成密钥
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_chengzigedeAir -N "" -C "7kecheng-to-chengzigedeAir"
cat ~/.ssh/id_ed25519_chengzigedeAir.pub
# 把输出的公钥发给 chengzigedeAir 加入到 ~/.ssh/authorized_keys
```

### 方式三：在 7kecheng 获取私钥内容

```
# 在 7kecheng 上执行:
# 复制以下完整内容到 ~/.ssh/id_ed25519_chengzigedeAir
```

## 公钥（已加入 chengzigedeAir 的 authorized_keys）

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIL9bYcGz5IsDKOEpyYKWsJj+CO8qF9fftK/Dtj2ZEZw8 7kecheng@chengzigedeAir
```
