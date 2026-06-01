#!/usr/bin/env python3
"""
LLM 分类器模块 - 使用 oMLX 本地大模型进行知识分类

功能：
1. 根据内容判断 nature（fact/method/concept/opinion/reference 等）
2. 根据内容判断 domain（技术/金融/产品/生活 等）
3. 提取关键信息（标题、摘要、标签）

配置：
- oMLX API: http://localhost:8000/v1/chat/completions
- 模型: Qwen3-8B-MLX-4bit
- API Key: omlx
"""

import json
import re
import time
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# ─── oMLX 配置 ──────────────────────────────────────────────────
OLLAMA_API_URL = "http://localhost:8000/v1/chat/completions"
OLLAMA_MODEL = "Qwen2.5-VL-3B-Instruct-8bit"  # 使用 VLM 模型，因为 Qwen3-8B-MLX-4bit 有 500 错误
OLLAMA_API_KEY = "omlx"

# 备份模型选项（如果 Qwen2.5 不可用）
FALLBACK_MODEL = "Qwen3-8B-MLX-4bit"

# ─── 分类体系 ──────────────────────────────────────────────────
NATURE_OPTIONS = [
    "fact",        # 客观事实、数据、统计结果
    "method",      # 方法、步骤、教程、最佳实践
    "concept",     # 概念、定义、理论、原理
    "opinion",     # 观点、看法、评价、推测
    "reference",   # 参考文献、论文、书籍、资料
    "quote",       # 引用、名言、摘录
    "axiom",       # 公理、定律、定理
    "regulation",  # 法规、政策、标准
    "data",        # 原始数据、数据集、代码片段
]

DOMAIN_OPTIONS = [
    "technology",      # 技术、编程、AI、开发
    "finance",         # 金融、投资、股票、经济
    "product",         # 产品、设计、UX、PM
    "life",            # 生活、健康、个人管理
    "academic",        # 学术、研究、教育
    "business",        # 商业、管理、创业
    "culture",         # 文化、艺术、娱乐
    "other",           # 其他
]

# ─── LLM 调用函数 ──────────────────────────────────────────────
def call_llm(prompt: str, system_prompt: str = None, temperature: float = 0.3) -> str:
    """
    调用 oMLX 本地大模型 API
    
    Args:
        prompt: 用户提示
        system_prompt: 系统提示（可选）
        temperature: 温度参数，越低越确定
    
    Returns:
        LLM 回复文本
    """
    import requests
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    try:
        # 首先尝试 VLM 模型
        resp = requests.post(
            OLLAMA_API_URL,
            json={
                "model": OLLAMA_MODEL,
                "messages": messages,
                "temperature": temperature,
                "stream": False
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OLLAMA_API_KEY}"
            },
            timeout=30
        )
        
        # 如果 VLM 模型失败（500 错误），尝试备选模型
        if resp.status_code == 500 and OLLAMA_MODEL == "Qwen2.5-VL-3B-Instruct-8bit":
            print(f"  ⚠️  VLM 模型失败，尝试备选模型 {FALLBACK_MODEL}")
            resp = requests.post(
                OLLAMA_API_URL,
                json={
                    "model": FALLBACK_MODEL,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": False
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {OLLAMA_API_KEY}"
                },
                timeout=30
            )
        
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[WARN] LLM 调用失败: {e}")
        return ""

# ─── 分类函数 ──────────────────────────────────────────────────
def classify_with_llm(text: str) -> Dict:
    """
    使用 LLM 对文本内容进行分类
    
    Args:
        text: 要分类的文本内容（Markdown 格式）
    
    Returns:
        {
            "nature": "fact/method/concept/...",
            "domain": "technology/finance/...",
            "confidence": 0.0-1.0,
            "title": "建议的标题",
            "summary": "简短摘要",
            "tags": ["标签1", "标签2", ...]
        }
    """
    # 限制文本长度（防止 token 过长）
    preview = text[:2000] if len(text) > 2000 else text
    
    system_prompt = """你是一个知识分类专家。请根据提供的文本内容进行以下分析：
1. 判断知识类型（nature）：从以下选项中选择最合适的：fact（事实数据）、method（方法步骤）、concept（概念理论）、opinion（观点看法）、reference（参考文献）、quote（引用摘录）、axiom（公理定律）、regulation（法规政策）、data（原始数据）
2. 判断所属领域（domain）：从以下选项中选择1-2个：technology（技术）、finance（金融）、product（产品）、life（生活）、academic（学术）、business（商业）、culture（文化）、other（其他）
3. 提取关键信息：建议一个简洁的标题、生成50字内的摘要、提取2-5个关键词标签

请以 JSON 格式返回结果，严格遵循以下结构：
{
    "nature": "选择的类型",
    "domain": ["领域1", "领域2"],
    "confidence": 0.0-1.0之间的数字（表示分类信心度），
    "title": "建议标题",
    "summary": "简短摘要",
    "tags": ["标签1", "标签2", "标签3"]
}"""

    user_prompt = f"""请对以下文本内容进行分类分析：

{preview}

注意：文本可能是截断的，请基于现有内容进行判断。"""

    response = call_llm(user_prompt, system_prompt, temperature=0.1)
    
    # 解析 JSON 响应
    result = {
        "nature": "concept",
        "domain": ["other"],
        "confidence": 0.5,
        "title": "",
        "summary": "",
        "tags": []
    }
    
    if not response:
        return result
    
    try:
        # 查找 JSON 部分
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            if isinstance(parsed, dict):
                if "nature" in parsed and parsed["nature"] in NATURE_OPTIONS:
                    result["nature"] = parsed["nature"]
                if "domain" in parsed:
                    if isinstance(parsed["domain"], str):
                        result["domain"] = [parsed["domain"]]
                    elif isinstance(parsed["domain"], list):
                        result["domain"] = [d for d in parsed["domain"] if d in DOMAIN_OPTIONS]
                if "confidence" in parsed:
                    try:
                        conf = float(parsed["confidence"])
                        if 0 <= conf <= 1:
                            result["confidence"] = conf
                    except:
                        pass
                if "title" in parsed:
                    result["title"] = str(parsed["title"])
                if "summary" in parsed:
                    result["summary"] = str(parsed["summary"])
                if "tags" in parsed:
                    if isinstance(parsed["tags"], list):
                        result["tags"] = [str(tag) for tag in parsed["tags"]]
    except Exception as e:
        print(f"[WARN] LLM 响应解析失败: {e}")
    
    return result

# ─── 启发式分类备用方案 ────────────────────────────────────────
def classify_heuristic(text: str, fm: dict) -> Dict:
    """
    启发式分类（当 LLM 不可用时使用）
    
    Args:
        text: 文本内容
        fm: 已有的 frontmatter
    
    Returns:
        与 classify_with_llm 相同结构的字典
    """
    result = {
        "nature": "concept",
        "domain": ["other"],
        "confidence": 0.4,
        "title": "",
        "summary": "",
        "tags": []
    }
    
    # 优先使用已有 frontmatter
    if fm.get("nature"):
        result["nature"] = fm["nature"]
    if fm.get("domain"):
        if isinstance(fm["domain"], str):
            result["domain"] = [fm["domain"]]
        elif isinstance(fm["domain"], list):
            result["domain"] = fm["domain"]
    
    # 启发式规则
    lower = text.lower()
    
    # nature 判断
    if not fm.get("nature"):
        method_kw = ["步骤", "教程", "如何", "how to", "方法", "指南", "最佳实践"]
        fact_kw = ["数据", "统计", "报告", "结果", "事实", "date", "report"]
        opinion_kw = ["认为", "觉得", "观点", "推测", "假设", "opinion", "think"]
        reference_kw = ["论文", "文献", "引用", "参考", "paper", "reference"]
        
        if any(kw in lower for kw in method_kw):
            result["nature"] = "method"
        elif any(kw in lower for kw in fact_kw):
            result["nature"] = "fact"
        elif any(kw in lower for kw in opinion_kw):
            result["nature"] = "opinion"
        elif any(kw in lower for kw in reference_kw):
            result["nature"] = "reference"
    
    # domain 判断
    if not fm.get("domain"):
        tech_kw = ["编程", "代码", "开发", "python", "javascript", "ai", "llm", "机器学习", "技术"]
        finance_kw = ["投资", "股票", "基金", "finance", "交易", "财经", "金融"]
        product_kw = ["产品", "设计", "ux", "product", "用户体验"]
        
        if any(kw in lower for kw in tech_kw):
            result["domain"] = ["technology"]
        elif any(kw in lower for kw in finance_kw):
            result["domain"] = ["finance"]
        elif any(kw in lower for kw in product_kw):
            result["domain"] = ["product"]
    
    # 生成简单标题（使用文件名或第一行）
    if fm.get("title"):
        result["title"] = fm["title"]
    else:
        first_line = text.split('\n')[0].strip('# ')
        if len(first_line) < 50:
            result["title"] = first_line
    
    # 生成简单摘要（前 100 字符）
    clean_text = re.sub(r'[#*\-`]', '', text)
    result["summary"] = clean_text[:100] + ("..." if len(clean_text) > 100 else "")
    
    return result

# ─── 主分类函数 ──────────────────────────────────────────────────
def classify_content_enhanced(text: str, fm: dict = None, use_llm: bool = True) -> Dict:
    """
    增强版分类函数：优先使用 LLM，失败时降级到启发式
    
    Args:
        text: 文本内容
        fm: 已有的 frontmatter（可选）
        use_llm: 是否尝试使用 LLM（默认 True）
    
    Returns:
        分类结果字典
    """
    if fm is None:
        fm = {}
    
    result = {
        "nature": "concept",
        "domain": ["other"],
        "confidence": 0.5,
        "title": "",
        "summary": "",
        "tags": [],
        "source_type": "unknown",
        "source": ""
    }
    
    # 优先使用已有 frontmatter
    if fm.get("nature"):
        result["nature"] = fm["nature"]
        result["confidence"] = max(result["confidence"], 0.7)  # 已有信息提升信心
    
    if fm.get("domain"):
        if isinstance(fm["domain"], str):
            result["domain"] = [fm["domain"]]
        elif isinstance(fm["domain"], list):
            result["domain"] = fm["domain"]
    
    # 尝试使用 LLM 分类
    llm_result = None
    if use_llm and text.strip():
        try:
            print("  🤖 使用 LLM 进行智能分类...")
            llm_result = classify_with_llm(text)
            
    # 合并 LLM 结果（降低阈值要求，因为 VLM 模型可能返回较低的 confidence）
    confidence_threshold = 0.4  # 降低阈值，因为 VLM 模型可能返回较低的 confidence
    if llm_result.get("confidence", 0) > confidence_threshold:
        if not fm.get("nature") and llm_result.get("nature"):
            result["nature"] = llm_result["nature"]
        if not fm.get("domain") and llm_result.get("domain"):
            result["domain"] = llm_result["domain"]
        if llm_result.get("title"):
            result["title"] = llm_result["title"]
        if llm_result.get("summary"):
            result["summary"] = llm_result["summary"]
        if llm_result.get("tags"):
            result["tags"] = llm_result["tags"]
        result["confidence"] = llm_result.get("confidence", 0.6)
        print(f"  ✅ LLM 分类成功 (confidence: {llm_result.get('confidence', 0.6):.2f})")
    else:
        print(f"  ⚠️  LLM 分类信心度低 ({llm_result.get('confidence', 0):.2f} < {confidence_threshold})，使用启发式规则")
        llm_result = None
        except Exception as e:
            print(f"  ⚠️  LLM 分类失败: {e}")
            llm_result = None
    
    # LLM 失败或信心不足，使用启发式规则
    if llm_result is None:
        heuristic_result = classify_heuristic(text, fm)
        
        # 合并启发式结果
        if not fm.get("nature") and heuristic_result.get("nature"):
            result["nature"] = heuristic_result["nature"]
        if not fm.get("domain") and heuristic_result.get("domain"):
            result["domain"] = heuristic_result["domain"]
        if not result["title"] and heuristic_result.get("title"):
            result["title"] = heuristic_result["title"]
        if not result["summary"] and heuristic_result.get("summary"):
            result["summary"] = heuristic_result["summary"]
    
    # 来源信息
    if fm.get("source"):
        result["source"] = fm["source"]
    if fm.get("source_type"):
        result["source_type"] = fm["source_type"]
    
    # 防止空列表
    if not result["domain"]:
        result["domain"] = ["other"]
    if not result["tags"]:
        result["tags"] = ["待补充"]
    
    return result

# ─── 测试函数 ──────────────────────────────────────────────────
if __name__ == "__main__":
    # 测试代码
    test_text = """Python 中的装饰器是一种强大的工具，它允许在不修改原函数代码的情况下，为函数添加额外的功能。

装饰器的基本语法：
@decorator
def my_function():
    pass

常见的装饰器应用场景包括：日志记录、性能测试、权限验证等。"""
    
    print("测试 LLM 分类：")
    result = classify_content_enhanced(test_text, use_llm=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    print("\n测试启发式分类（关闭 LLM）：")
    result2 = classify_content_enhanced(test_text, use_llm=False)
    print(json.dumps(result2, ensure_ascii=False, indent=2))