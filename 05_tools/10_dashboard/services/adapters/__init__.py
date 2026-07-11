"""
采集适配器基类 — 统一接口

每个平台适配器实现 CollectAdapter 接口：
  - collect_item(target, depth, tool_level) -> dict
  - collect_user(user_id, limit) -> list[dict]
  - collect_comments(item_id, limit) -> list[dict]
  - collect_search(keyword, limit) -> list[dict]

工具降级：
  Level 1: OpenCLI（仅 CLI）
  Level 2: OpenCLI → agent-browser（默认）
  Level 3: OpenCLI → agent-browser → web_crawler
"""

import asyncio, json, subprocess, logging, os
from pathlib import Path

logger = logging.getLogger("dashboard.collect.adapter")


class CollectAdapter:
    """采集适配器基类"""

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

    async def _run_opencli(self, args: list, timeout: int = 60) -> dict:
        """执行 OpenCLI 命令并解析 JSON 输出"""
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
        # 解析 YAML 格式输出（OpenCLI 默认输出 YAML）
        return self._parse_yaml_output(output)

    def _parse_yaml_output(self, text: str) -> list:
        """解析 OpenCLI 的 YAML 表格输出为列表"""
        items = []
        current = {}
        for line in text.split("\n"):
            line = line.strip()
            if not line or line.startswith("---"):
                if current:
                    items.append(current)
                    current = {}
                continue
            if ": " in line:
                k, v = line.split(": ", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                # 处理嵌套
                if k == "top_comments":
                    current[k] = []
                elif k in ("text", "nickname", "digg_count") and "top_comments" in current:
                    if isinstance(current["top_comments"], list):
                        if current["top_comments"] and k in current["top_comments"][-1]:
                            pass
                        entry = {"text": "", "nickname": "", "digg_count": 0}
                        entry[k] = v
                        current["top_comments"].append(entry)
                else:
                    current[k] = v
        if current:
            items.append(current)
        return items

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
