"""
抓取适配器基类 — 统一接口

每个平台适配器实现 ScrapeAdapter 接口：
  - collect_item(target, depth, tool_level) -> dict
  - collect_user(user_id, limit) -> list[dict]
  - collect_comments(item_id, limit) -> list[dict]
  - collect_search(keyword, limit) -> list[dict]

工具降级：
  Level 1: OpenCLI（仅 CLI）
  Level 2: OpenCLI → agent-browser（默认）
  Level 3: OpenCLI → agent-browser → web_crawler
"""

import asyncio, json, logging, os
from pathlib import Path

logger = logging.getLogger("dashboard.scrape.adapter")


class ScrapeAdapter:
    """抓取适配器基类"""

    platform = ""       # 子类覆写
    adapter_name = ""

    # OpenCLI 二进制路径
    OPENCLI = os.environ.get("OPENCLI_PATH",
        str(Path.home() / ".workbuddy" / "binaries" / "node" / "versions" / "22.22.2" / "bin" / "opencli"))

    # ── 工具降级 ──

    async def _try_tools(self, tool_level: int, funcs: list) -> tuple:
        """
        按降级顺序尝试工具。
        funcs: [(tool_name, callable), ...]
        返回: (success, result, used_tool)
        """
        tools = [f for f in funcs[:tool_level]]
        for name, fn in tools:
            try:
                result = await fn()
                if result is not None:
                    return True, result, name
            except Exception as e:
                logger.warning(f"  ⚠️ [{self.platform}] 工具 {name} 失败: {e}")
        return False, None, tools[-1][0] if tools else "none"

    async def _run_opencli(self, args: list, timeout: int = 60):
        """
        执行 OpenCLI 命令并解析输出。

        自动检测输出格式：
          1. JSON（以 [ 或 { 开头）→ json.loads
          2. YAML（PyYAML 可用时） → yaml.safe_load
          3. 兜底 → 简易 key:value 行解析
        """
        cmd = [self.OPENCLI] + args
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            raise TimeoutError(f"OpenCLI 超时 ({timeout}s): {' '.join(args[:4])}")
        if proc.returncode != 0:
            err = stderr.decode().strip() or stdout.decode()[:200]
            raise RuntimeError(f"OpenCLI 错误 ({proc.returncode}): {err}")
        output = stdout.decode().strip()
        if not output:
            return {}
        return self._parse_output(output)

    def _parse_output(self, text: str):
        """
        解析 OpenCLI 输出，自动检测格式。
        返回 list[dict] 或 dict。
        """
        text = text.strip()
        if not text:
            return {}

        # 1. JSON 检测（以 [ 或 { 开头）
        if text.startswith("[") or text.startswith("{"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                logger.warning("  ⚠️ OpenCLI JSON 解析失败，尝试 YAML 兜底")

        # 2. YAML 解析（PyYAML 在 requirements.txt 中）
        try:
            import yaml
            parsed = yaml.safe_load(text)
            if parsed is not None:
                return parsed
        except ImportError:
            logger.debug("  PyYAML 未安装，跳过 YAML 解析")
        except Exception as e:
            logger.warning(f"  ⚠️ YAML 解析失败: {e}")

        # 3. 兜底：简易 key:value 行解析（无依赖）
        return self._parse_lines(text)

    def _parse_lines(self, text: str) -> list:
        """
        最后一层兜底：按行解析 key:value 格式输出。
        适用于没有 yaml 库或 JSON/YAML 都失败的情况。
        """
        items = []
        current = {}
        # 尝试识别表格/列表分隔符
        in_top_comments = False
        comment_buffer = []

        def _maybe_flush():
            """将当前记录推入 items"""
            nonlocal current, comment_buffer, in_top_comments
            # 处理缓存的评论
            if comment_buffer:
                current["top_comments"] = comment_buffer
                comment_buffer = []
            if current and any(v for v in current.values()):
                items.append(current)
            current = {}
            in_top_comments = False

        for line in text.split("\n"):
            line_stripped = line.strip()
            if not line_stripped:
                _maybe_flush()
                continue
            # 分隔线（--- 或 =====）
            if line_stripped.startswith("---") or line_stripped.startswith("==="):
                _maybe_flush()
                continue
            # key: value 行
            if ": " in line_stripped:
                k, v = line_stripped.split(": ", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                # 特殊字段: top_comments
                if k == "top_comments":
                    _maybe_flush()
                    in_top_comments = True
                    comment_buffer = []
                elif k in ("nickname", "text", "digg_count") and in_top_comments:
                    # 评论块中的字段
                    if comment_buffer and k in comment_buffer[-1]:
                        # 同 key 出现多次 → 新评论
                        pass
                    entry = comment_buffer[-1] if comment_buffer else {}
                    entry[k] = v
                    if not comment_buffer:
                        comment_buffer.append(entry)
                    else:
                        # 如果当前 entry 已经有这个 key 了，说明是新记录
                        if k in comment_buffer[-1] and comment_buffer[-1][k] != v:
                            comment_buffer.append({k: v})
                        else:
                            comment_buffer[-1][k] = v
                elif in_top_comments:
                    # 在 top_comments 块里但字段不在三个已知中 → 只是浮层
                    pass
                else:
                    current[k] = v
            # 列表项（以 - 开头）
            elif line_stripped.startswith("- "):
                _maybe_flush()
                val = line_stripped[2:].strip()
                if val:
                    current = {"_value": val}
                    items.append(current)
                    current = {}

        _maybe_flush()
        return items if items else [current] if current else []

    # ── 接口方法（子类覆写）──

    async def collect_item(self, target: str, depth: str = "light",
                           tool_level: int = 2) -> dict:
        raise NotImplementedError

    async def collect_user(self, user_id: str, limit: int = 20) -> list[dict]:
        raise NotImplementedError

    async def collect_comments(self, item_id: str, limit: int = 20) -> list[dict]:
        raise NotImplementedError

    async def collect_search(self, keyword: str, limit: int = 20) -> list[dict]:
        raise NotImplementedError
