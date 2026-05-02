# HOST_ID.md —— 本机标识与角色

> 本机身份文件，存储于 agent-local/identity/HOST_ID.md  
> 首次初始化时自动生成，可手动修改角色和能力开关

---

## 主机信息

- 主机名: __HOSTNAME__
- 系统: __OS_INFO__
- 角色: master
- 创建时间: __INIT_TIME__

## 角色说明

| 角色 | 权限 | 执行任务 |
|------|------|---------|
| master | 读写全部协同目录 | 知识提纯/记忆汇总/核心维护 |
| maintainer | 写入提交箱 | 内容采集/本地记忆/提交有价值内容 |
| node | 只提交 | 信息采集/素材上传 |

## 能力开关

修改以下值以控制本机功能：

```yaml
# 记忆类
memory_digestion: true          # 本机记忆提炼
memory_export: true             # 提交有价值记忆到主库

# 知识类
knowledge_collection: true      # 内容采集
knowledge_refinement: false     # 知识库提纯（仅 master 设为 true）
knowledge_publish: false        # 知识库发布（仅 master 设为 true）

# 自动化
auto_collector: true            # 定时采集
inbox_refine: false             # 收件箱提纯（仅 master 设为 true）
git_sync_push: false            # Git推送（仅 master 设为 true）
```

## 角色切换

修改上方 `角色` 字段后，重启相关任务即可生效。
各自动化脚本执行时会自动检查角色，不匹配则跳过。
