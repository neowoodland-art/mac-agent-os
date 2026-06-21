# AgentOS 修复方案与落地清单

> 版本: 1.0 | 基于 2026-06-21 审计报告
> 按优先级排列，每项含：耗时 / 风险 / 前置依赖

---

## 第一步：Git 仓库减肥（P0，立刻做）

### 1.1 诊断：先看什么东西在吃空间

```bash
# 进入仓库
cd ~/workbuddy-agent-os/agent-sync

# 1. 看总大小
du -sh .git                          # .git 目录大小（预估 400MB）
du -sh .                             # 工作树大小（预估 600MB）

# 2. 找最大的文件（被 git 追踪的）
git rev-list --objects --all | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
  awk '/^blob/ {print $3, $4}' | \
  sort -rn | head -20

# 3. 看哪些大文件类型在 git 索引里
git ls-files | grep -E '\.(png|jpg|jpeg|gif|svg|ico|pdf)$'
git ls-files | grep -E '\.(so|dylib|a|o)$'
git ls-files | grep -E '(profiles|cache|chroma|node_modules)'
```

**预期发现：** 大文件来源通常是：
1. 浏览器 Profile 文件夹（曾未加 .gitignore 时被提交过）
2. 截图 .png 文件（dashboard、matrix screenshots）
3. ChromaDB SQLite 文件
4. Python .so 编译文件
5. longcat 浏览器缓存

---

### 1.2 更新 .gitignore（排除所有不该进 Git 的东西）

在现有 `.gitignore` 末尾追加：

```
# ────── v4.2.0 新增排除项 ──────

# 图片文件（截图、素材，不入库）
*.png
*.jpg
*.jpeg
*.gif
*.svg
*.ico
*.webp

# ChromaDB 数据（各机独立）
chroma.sqlite3
**/chroma/

# 前端构建产物
node_modules/
dist/
build/

# ML 模型文件
*.pth
*.bin
*.onnx
*.npy
*.npz

# 运行时数据目录
cross_machine/data/

# Matrix 截图
05_tools/07_matrix/screenshots/

# AVE 输出
09_ave/output/
09_ave/cache/

# 系统报告归档
reports/

# Dashboard 前端产物
05_tools/10_dashboard/frontend/node_modules/
05_tools/10_dashboard/frontend/dist/
```

---

### 1.3 从 Git 追踪中移除已在大文件（不删文件，只删追踪）

```bash
# 对每一类已追踪的大文件执行 git rm --cached

# 1. 移除所有图片文件（如果被追踪过）
git rm --cached -r --ignore-unmatch 05_tools/07_matrix/screenshots/
git rm --cached -r --ignore-unmatch 05_tools/10_dashboard/*.png
git ls-files | grep -E '\.(png|jpg|jpeg|gif)$' | xargs -r git rm --cached

# 2. 移除浏览器 Profile（如果被追踪过）
git rm --cached -r --ignore-unmatch 05_tools/07_matrix/profiles/
git rm --cached -r --ignore-unmatch 05_tools/05_crawl/longcat/profiles/

# 3. 移除 ChromaDB 数据
git rm --cached -r --ignore-unmatch 04_memory/vector_db/
git ls-files | grep chroma | xargs -r git rm --cached

# 4. 移除运行时数据
git rm --cached -r --ignore-unmatch cross_machine/data/
git rm --cached -r --ignore-unmatch 04_memory/cross_machine/data/

# 5. 移除旧的迁移目录
git rm --cached -r --ignore-unmatch 07_migration/

# 6. 提交本次清理
git commit -m "chore(git): 清理已追踪的大文件，更新 .gitignore v4.2.0"
```

---

### 1.4 重写 Git 历史以永久删除大文件（可选但推荐）

> ⚠️ 这一步会改变 commit hash，所有机器需要重新 clone。
> **但如果 1.3 步提交后，远程仓库大小仍然不变，就必须做这一步。**
> 因为历史 commit 中仍然保留着大文件——.gitignore 和 git rm 只影响未来。

**方案 A：使用 git filter-repo（推荐）**

```bash
# 安装 git-filter-repo
pip install git-filter-repo

# 在全新 clone 上操作（不要在原仓库，防止意外）
cd /tmp
git clone ~/workbuddy-agent-os/agent-sync agentos-clean
cd agentos-clean

# 删除历史中所有 .png/.jpg/.so/.mp4 等大文件
git filter-repo \
  --path-glob '*.png' --path-glob '*.jpg' --path-glob '*.so' \
  --path-glob '*.mp4' --path-glob 'chroma.sqlite3' \
  --path '05_tools/07_matrix/profiles/' \
  --path '05_tools/05_crawl/longcat/profiles/' \
  --path '04_memory/vector_db/' \
  --invert-paths

# 验证大小
du -sh .git

# 如果还是大，再按大小找 Top offenders
git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectsize) %(rest)' | sort -rn | head -20
```

**方案 B：使用 BFG Repo-Cleaner（更简单）**

```bash
# 下载 BFG
wget https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar

# 清理 >10MB 的文件
java -jar bfg-1.14.0.jar --strip-blobs-bigger-than 10M agentos-clean

# 清理指定模式
java -jar bfg-1.14.0.jar --delete-files '*.png' agentos-clean
java -jar bfg-1.14.0.jar --delete-files '*.so' agentos-clean
```

**方案 C：如果 filter-repo 太复杂，最小化方案**

```bash
# 只清理最大的文件类型，保留历史完整性
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch -r \
    05_tools/07_matrix/profiles/ \
    05_tools/05_crawl/longcat/profiles/ \
    04_memory/vector_db/ \
    07_migration/" \
  --prune-empty --tag-name-filter cat -- --all

# 回收空间
git reflog expire --expire=now --all
git gc --aggressive --prune=now
```

---

### 1.5 推送到远程（所有操作完成后）

```bash
# 强制推送（因为历史被重写了）
git push origin --force --all
git push origin --force --tags

# 验证远程仓库大小
curl -s https://api.github.com/repos/babycalf/mac-agent-os | grep "size"
# size 单位是 KB，目标 < 50000（即 < 50MB）
```

---

### 1.6 其他机器重新 clone

```bash
# 5kechengdeAir 和 7kecheng 上执行
cd ~
mv workbuddy-agent-os workbuddy-agent-os.bak  # 备份旧目录
git clone git@gitee.com:babycalf/mac-agent-os.git workbuddy-agent-os/agent-sync
cd workbuddy-agent-os/agent-sync && bash 00_bootstrap/init.sh
```

---

### 1.7 验证结果

```bash
# 1. 本地仓库大小
du -sh .git                              # 期望 < 50MB
du -sh .                                 # 期望 < 100MB（不含 agent-local/）

# 2. 不再有大文件被追踪
git ls-files | grep -E '\.(png|jpg|so|mp4)$'  # 期望 0 结果

# 3. agentos check 仍然通过
cd ~/workbuddy-agent-os/agent-sync
python3 -m agentos check --quick

# 4. clone 速度测试（从另一台机器）
time git clone git@gitee.com:babycalf/mac-agent-os.git test-clone
# 期望 < 30 秒（之前可能 > 5 分钟）
```

---

## 第二步：修复高优问题（P1）

完成 Git 减肥后，按以下顺序修复：

| 优先级 | 问题 | 方案 | 预估工时 |
|:------:|:-----|:-----|:--------|
| P1-1 | **oMLX Chat API 500** | 诊断 Qwen3-8B 错误 → 尝试降级/换模型/用 VLM 替代 | 1-2h |
| P1-2 | **collect_to_inbox v2.0** | 补全 01_submissions/ 扫描逻辑（约 40 行代码） | 2h |
| P1-3 | **AVE service_layer 空目录** | 确认 09_ave TOOL.md 说的 API 是否需要 → 补全或降级文档 | 1h |
| P1-4 | **agentos check 增加宪法对账** | 在 check.py 中比较 CONSTITUTION.md 版本 vs 实际代码一致性 | 2h |
| P1-5 | **删除 accounts_registry.yaml** | 确认无代码引用后删除（已标记废弃） | 10min |

---

## 第三步：中期改进（P2）

| 优先级 | 问题 | 方案 | 预估 |
|:------:|:-----|:-----|:-----|
| P2-1 | **app.py 1521 行拆分** | 按已有 routes/ 目录拆分为 3-4 个路由模块 | 1d |
| P2-2 | **添加测试基础** | guardd 核心模块 + semantic_search RRF 写单元测试 | 1d |
| P2-3 | **统一日志格式** | 所有 Python 模块使用 logging + 统一格式字符串 | 4h |
| P2-4 | **双 agentos 插件加载加固** | 把 07_matrix/agentos/plugins/ 复制到 00_setup/agentos/federation_plugins/ | 2h |
| P2-5 | **FEDERATION_GUIDE.md 完整对账** | 遍历全文确认所有数字与实际一致 | 2h |

---

## 第四步：长期优化（P3）

| 项目 | 说明 | 预估 |
|:-----|:------|:-----|
| CommandCenter | 实时跨机通信，替代 15min Git 同步延迟 | 2-4 周 |
| 独立运行模式 | 脱离 WorkBuddy 也可运行 | 2-3 周 |
| 技能市场 | SKILL_CARD.yaml 标准化 + 社区技能安装 | 1-2 周 |
| 内容工厂 | 采集→AI 分析→AVE 生成→自动发布全流水线 | 3-4 周 |

---

## 落地路线图（甘特图）

```
时间线      今天      本周      下周      下月      季度
            │        │        │        │        │
Git 减肥    ████████▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░
诊断+清理       ██████▓
filter-repo           ██████▓
各机re-clone                ██▓
────────────────────────────────────────────────
oMLX 修复           ██████▓
collect_to_inbox           ██████▓
AVE 确认                       ██▓
宪法对账                         ██▓
────────────────────────────────────────────────
app.py 拆分                        ██████████▓
测试基础                             ██████▓
统一日志                                ██████▓
────────────────────────────────────────────────
CommandCenter                               ████████████▓
独立运行                                         ████████████▓
```

---

## 执行建议

### 执行的顺序很关键

```
第一步做 Git 减肥 → 然后再做其他事情
                     ↑
               如果不先做这个：
               - 其他机器 git pull 要等 5 分钟
               - push 频繁超时
               - 新机器部署痛苦
```

### 每个步骤的风险控制

```
Git filter-repo 前：
  ✅ 备份原仓库（tar czf backup.tar.gz .git）
  ✅ 在临时目录操作（不在原目录）
  ✅ 先在一台机器验证，再通知其他机器
  ✅ 准备好 rollback 方案
```

### 日常维护习惯

```bash
# 每次 push 前快速检查
du -sh .git                              # 超过 100MB 要警惕
git ls-files | grep -E '\.(png|jpg|so)$' # 应为空
git status --porcelain | wc -l           # 干净工作区

# 每月一次深度检查
git count-objects -v                     # 看 pack 文件数量和大小
```
