#!/usr/bin/env python3
"""
vision_bridge.py — AgentOS 视觉分析桥接层

职责：
  将截图发送给 oMLX Qwen2.5-VL 模型，返回结构化页面描述。
  供原子操作和视觉Recipe使用。

用法：
  from vision_bridge import analyze_screenshot, describe_page

  # 分析页面
  result = analyze_screenshot("screenshot.png", "What buttons are visible?")
  print(result["text"])

  # 快捷：描述整个页面
  page = describe_page("screenshot.png")
  print(page["elements"])  # 列表
"""
import json, urllib.request, base64, time, os, sys
from pathlib import Path
from typing import Optional

# ── 配置 ──────────────────────────────────────────────
OMLX_BASE = "http://127.0.0.1:8000"
OMLX_API_KEY = "omlx"
OMLX_MODEL = "Qwen2.5-VL-3B-Instruct-8bit"
VISION_TIMEOUT = 300  # 秒
TEXT_TIMEOUT = 30

# DashScope (阿里百炼) 配置
DASHSCOPE_API_KEY = "sk-7e62716bffe349a59e74e9182cf22c3a"
DASHSCOPE_MODEL = "qwen-vl-plus"  # 性价比高

# 代理问题：oMLX 不能用代理
_orig_env = {}


def _ensure_no_proxy():
    """临时去掉代理（oMLX 不能走代理）"""
    global _orig_env
    for k in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"]:
        _orig_env[k] = os.environ.pop(k, None)


def _restore_proxy():
    for k, v in _orig_env.items():
        if v is not None:
            os.environ[k] = v


# ── 核心 API ─────────────────────────────────────────

def _omlx_request(messages: list, max_tokens: int = 300, timeout: int = None) -> dict:
    """向 oMLX 发送请求（本地）"""
    _ensure_no_proxy()
    try:
        data = json.dumps({
            "model": OMLX_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
        }).encode()

        req = urllib.request.Request(f"{OMLX_BASE}/v1/chat/completions", data=data)
        req.add_header("Content-Type", "application/json")
        req.add_header("x-api-key", OMLX_API_KEY)

        resp = urllib.request.urlopen(req, timeout=timeout or VISION_TIMEOUT)
        result = json.loads(resp.read())
        return {
            "success": True,
            "text": result["choices"][0]["message"]["content"],
            "usage": result.get("usage", {}),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "provider": "omlx"}
    finally:
        _restore_proxy()


def _dashscope_request(messages: list, max_tokens: int = 300, timeout: int = None) -> dict:
    """向 DashScope (阿里百炼) 发送请求（远程）"""
    try:
        import dashscope
        dashscope.api_key = DASHSCOPE_API_KEY

        resp = dashscope.MultiModalConversation.call(
            model=DASHSCOPE_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            timeout=timeout or VISION_TIMEOUT,
        )
        if resp.status_code == 200:
            content = resp.output.choices[0].message.content[0]["text"]
            return {"success": True, "text": content, "usage": resp.usage, "provider": "dashscope"}
        return {"success": False, "error": f"DashScope {resp.status_code}: {resp.message}", "provider": "dashscope"}
    except ImportError:
        return {"success": False, "error": "dashscope SDK 未安装", "provider": "dashscope"}
    except Exception as e:
        return {"success": False, "error": str(e), "provider": "dashscope"}


def _request(messages: list, max_tokens: int = 300, timeout: int = None) -> dict:
    """自动选择：oMLX 本地优先 → DashScope 远程兜底"""
    result = _omlx_request(messages, max_tokens, timeout)
    if result["success"]:
        return result
    # oMLX 失败 → 用 DashScope
    print(f"  [vision] oMLX 不可用 ({result.get('error','?')}), 切换到 DashScope...")
    result2 = _dashscope_request(messages, max_tokens, timeout)
    return result2


def _encode_image(image_path: str) -> str:
    """读取图片并编码为 base64"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# ── 公开接口 ─────────────────────────────────────────

def analyze_screenshot(image_path: str, question: str,
                       max_tokens: int = 500, timeout: int = None) -> dict:
    """
    分析截图，返回模型回答。

    Args:
        image_path: 截图路径
        question: 问题，如 "What buttons are visible?"
        max_tokens: 最大生成长度
        timeout: 超时秒数

    Returns:
        {"success": bool, "text": str, "error": str, "usage": dict}
    """
    if not os.path.isfile(image_path):
        return {"success": False, "error": f"File not found: {image_path}"}

    img_b64 = _encode_image(image_path)
    messages = [{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
            {"type": "text", "text": question}
        ]
    }]

    t0 = time.time()
    result = _request(messages, max_tokens, timeout)
    result["elapsed"] = round(time.time() - t0, 1)
    return result


def describe_page(image_path: str) -> dict:
    """
    分析页面整体结构：布局、按钮、输入框、导航等。

    Returns:
        {"success": bool, "elements": [...], "error": str}
    """
    result = analyze_screenshot(image_path,
        "Describe this page in detail. List all: "
        "1) Navigation/sidebar items and their labels "
        "2) Buttons and their text "
        "3) Text fields and input areas "
        "4) The main content area. "
        "Be specific about what each element says.",
        max_tokens=800)

    if not result["success"]:
        return result

    # 解析成结构化元素（后续可增强）
    text = result["text"]
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    return {
        "success": True,
        "elements": lines,
        "raw_text": text,
        "elapsed": result.get("elapsed", 0),
        "usage": result.get("usage", {}),
    }


def find_element(image_path: str, target_label: str) -> dict:
    """
    查找指定文字/标签的元素位置。

    Args:
        image_path: 截图路径
        target_label: 要找的标签，如 "登录"、"继续"

    Returns:
        {"success": bool, "found": bool, "description": str}
    """
    result = analyze_screenshot(image_path,
        f'Is there a "{target_label}" button, link, or text field visible? '
        f'If yes, describe exactly where it appears on the page and what it looks like.',
        max_tokens=200)
    return result


def text_chat(prompt: str, max_tokens: int = 100) -> dict:
    """纯文本对话（不走视觉，速度更快）"""
    messages = [{"role": "user", "content": prompt}]
    t0 = time.time()
    result = _request(messages, max_tokens, TEXT_TIMEOUT)
    result["elapsed"] = round(time.time() - t0, 1)
    return result


# ── 命令行入口 ───────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Vision Bridge - 截图分析工具")
    parser.add_argument("image", nargs="?", help="截图路径")
    parser.add_argument("-q", "--question", default="Describe this page briefly.",
                        help="分析问题")
    parser.add_argument("-f", "--find", help="查找指定元素")
    parser.add_argument("--list", action="store_true", help="列出页面所有元素")

    args = parser.parse_args()

    if args.find and args.image:
        result = find_element(args.image, args.find)
    elif args.list and args.image:
        result = describe_page(args.image)
    elif args.image:
        result = analyze_screenshot(args.image, args.question)
    else:
        # 默认交互模式
        img = input("截图路径: ").strip() or "/Users/chengzige/.agent-browser/tmp/screenshots/screenshot-1781835723294.png"
        q = input("问题: ").strip() or "What is on this page?"
        result = analyze_screenshot(img, q)

    if result.get("success"):
        print(f"\n=== 回答 (耗时: {result.get('elapsed', '?')}s) ===")
        print(result.get("text", ""))
        if "usage" in result:
            print(f"\nToken: {result['usage']}")
    else:
        print(f"\n❌ 失败: {result.get('error', '未知错误')}")
        sys.exit(1)
