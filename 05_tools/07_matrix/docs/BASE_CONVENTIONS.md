# Matrix 基础操作约定 v1.0

> **最后更新**：2026-05-10
> **适用范围**：所有原子操作

---

## 约定 1：窗口焦点（每次操作前必做）

**规则**：所有键盘操作、鼠标操作、页面交互前，必须先确保浏览器窗口在最前端。

**实现**：每个原子操作的 pre-check 阶段，先执行 `_activate_window()`。

```python
async def _activate_window():
    """AppleScript 将 Camoufox 窗口置顶"""
    script = 'tell application "System Events" to set frontmost of every process whose name contains "camoufox" to true'
    subprocess.run(['osascript', '-e', script], capture_output=True, timeout=3)
```

这个调用放在每个原子操作执行函数的最前面。

---

## 约定 2：双击模式

**规则**：所有"点击进入"类操作使用双击模式。
- 第1次点击：获取焦点 / 激活窗口 / 使元素可交互
- 等待 1 秒
- 第2次点击：真正的操作

---

## 约定 3：优雅关闭浏览器

**规则**：每次脚本启动前：
1. 检测是否有运行的 Camoufox 进程
2. 如有 → `pkill -f camoufox` → 等待 3 秒
3. 删除 `.parentlock` 锁文件
4. 再启动

**实现**：在 `CDPConnector.connect()` 中自动执行。

---

## 约定 4：错误报告格式

当任何一个原子操作失败时，**必须**按以下格式报告，不自行修复：

```
❌ 操作失败报告
═══════════════════
当前状态: [状态码]
当前页面: [URL]
当前页面标题: [title]
失败操作: [操作名]
失败阶段: [pre/execute/post]
失败原因: [具体错误信息/不符合的特征码]
预期后置状态: [状态码]
实际检测状态: [状态码]
环境: 窗口[W×H] 位置([X],[Y]) 激活态[Y/N]
═══════════════════
等待指示...
```

---

## 约定 5：交互测试流程

每个原子操作测试流程：
1. 我启动浏览器到起始状态
2. 我报告当前状态的特征码，你确认
3. 你指示 "可以执行"
4. 我执行该原子操作
5. 我报告结果（成功/失败+特征码变化）
6. 你指示下一步
