"""
口播素材系统 - AI 分析脚本
用法：python analyze.py [--limit N] [--retry-failed]

功能：
  1. 查询所有未分析的素材记录
  2. 调用本地 oMLX（Qwen2.5-VL-3B）进行口播价值分析
  3. 解析结构化 JSON 结果，写入 analysis 表

本机适配：
  - 使用 oMLX HTTP API（localhost:8000），非 Ollama
  - 模型：Qwen2.5-VL-3B-Instruct-8bit
  - 串行执行，防止 16GB 内存 OOM
  - 异常自动跳过，不中断整体流程
"""

import os
import sys
import json
import re
import argparse
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx
from utils import load_config, get_db, init_db, setup_logger

# 分析提示词模板
ANALYSIS_PROMPT = """你是一个口播素材分析助手。请分析以下内容，提取口播创作可用的信息。仅返回合法JSON，不要有任何额外文字。

内容：
标题：{title}
描述：{description}
作者：{author}
平台：{platform}

要求返回JSON：
{{
  "tags": ["标签1","标签2","标签3"],
  "golden_quote": "可以直接引用的金句或观点，不超过30字",
  "core_idea": "一句话核心立意",
  "structure": "口播脚本结构：开头-中间-结尾的梗概",
  "emotion": "整体情绪，如 治愈/励志/震惊/沉思/有趣",
  "worth_downloading": "yes/no/maybe",
  "download_reason": "建议下载的简短理由，若no则留空"
}}"""


def call_omlx(prompt: str, config: dict, logger) -> str | None:
    """
    调用 oMLX API 进行推理

    返回：模型输出的文本，失败返回 None
    """
    import httpx
    try:
        resp = httpx.post(
            f"{config['llm']['base_url']}/chat/completions",
            headers={
                "Authorization": f"Bearer {config['llm']['api_key']}",
                "Content-Type": "application/json",
            },
            json={
                "model": config["llm"]["model"],
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": config["llm"].get("temperature", 0.3),
                "max_tokens": 500,
            },
            timeout=config["llm"].get("timeout", 120),
        )
        
        if resp.status_code != 200:
            logger.error(f"oMLX 返回 {resp.status_code}: {resp.text[:200]}")
            return None
        
        return resp.json()["choices"][0]["message"]["content"]
    
    except httpx.TimeoutException:
        logger.error("oMLX 请求超时")
        return None
    except Exception as e:
        logger.error(f"oMLX 调用异常: {e}")
        return None


def parse_analysis_json(raw_text: str, logger) -> dict | None:
    """
    解析模型输出的 JSON，带容错处理
    """
    if not raw_text:
        return None
    
    # 尝试直接解析
    try:
        result = json.loads(raw_text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass
    
    # 尝试提取 JSON 块（模型可能输出 ```json ... ```）
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(1))
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass
    
    # 尝试提取第一个 { 到最后一个 }
    first = raw_text.find("{")
    last = raw_text.rfind("}")
    if first != -1 and last != -1 and last > first:
        try:
            result = json.loads(raw_text[first:last+1])
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass
    
    logger.warning(f"JSON 解析失败，原始输出: {raw_text[:200]}")
    return None


def analyze_one(material: dict, config: dict, logger) -> dict | None:
    """
    分析单条素材
    """
    title = material["title"] or ""
    description = (material.get("description") or "")[:500]  # 截断避免过长
    
    if not title and not description:
        logger.warning(f"素材 {material['id']} 无标题和描述，跳过")
        return None
    
    prompt = ANALYSIS_PROMPT.format(
        title=title,
        description=description,
        author=material.get("author", "未知"),
        platform=material.get("platform", "未知"),
    )
    
    raw_output = call_omlx(prompt, config, logger)
    if not raw_output:
        return None
    
    result = parse_analysis_json(raw_output, logger)
    if not result:
        return None
    
    # 规范化字段
    return {
        "material_id": material["id"],
        "tags": ",".join(result.get("tags", [])),
        "golden_quote": str(result.get("golden_quote", ""))[:200],
        "core_idea": str(result.get("core_idea", ""))[:300],
        "structure": str(result.get("structure", ""))[:500],
        "emotion": str(result.get("emotion", ""))[:20],
        "worth_downloading": str(result.get("worth_downloading", "no"))[:10],
        "download_reason": str(result.get("download_reason", ""))[:200],
        "raw_model_output": raw_output,
    }


def main():
    parser = argparse.ArgumentParser(description="口播素材 AI 分析")
    parser.add_argument("--limit", "-n", type=int, default=0, help="分析数量上限，0=全部")
    parser.add_argument("--retry-failed", action="store_true", help="重试分析失败的记录")
    parser.add_argument("--dry-run", action="store_true", help="仅显示待分析数量，不执行")
    args = parser.parse_args()
    
    config = load_config()
    logger = setup_logger("analyze")
    
    # 检查 oMLX
    from utils import check_omlx
    if not check_omlx(config):
        logger.error("oMLX 不可用，请先启动 oMLX 服务")
        return
    
    db_path = init_db()
    db = get_db(db_path)
    
    # 查询待分析记录
    if args.retry_failed:
        query = "SELECT * FROM materials WHERE analyzed = 2"
    else:
        query = "SELECT * FROM materials WHERE analyzed = 0"
    
    if args.limit > 0:
        query += f" LIMIT {args.limit}"
    
    materials = db.execute(query).fetchall()
    materials = [dict(m) for m in materials]
    
    if not materials:
        print("[OK] 没有待分析的素材")
        db.close()
        return
    
    print(f"[INFO] 待分析: {len(materials)} 条")
    
    if args.dry_run:
        for m in materials[:5]:
            print(f"  - [{m['platform']}] {m['title'][:40]}")
        if len(materials) > 5:
            print(f"  ... 还有 {len(materials) - 5} 条")
        db.close()
        return
    
    success = 0
    failed = 0
    
    for i, material in enumerate(materials, 1):
        print(f"\r[进度] {i}/{len(materials)} 分析中...", end="", flush=True)
        
        try:
            result = analyze_one(material, config, logger)
            
            if result:
                # 写入 analysis 表
                db.execute("""
                    INSERT OR REPLACE INTO analysis 
                    (material_id, tags, golden_quote, core_idea, structure,
                     emotion, worth_downloading, download_reason, raw_model_output)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    result["material_id"], result["tags"], result["golden_quote"],
                    result["core_idea"], result["structure"], result["emotion"],
                    result["worth_downloading"], result["download_reason"],
                    result["raw_model_output"],
                ))
                # 更新素材分析状态
                db.execute("UPDATE materials SET analyzed = 1 WHERE id = ?", (material["id"],))
                db.commit()
                success += 1
            else:
                db.execute("UPDATE materials SET analyzed = 2 WHERE id = ?", (material["id"],))
                db.commit()
                failed += 1
            
            # 间隔 1 秒，避免过载
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"分析异常 [{material['id']}]: {e}")
            db.execute("UPDATE materials SET analyzed = 2 WHERE id = ?", (material["id"],))
            db.commit()
            failed += 1
    
    db.close()
    
    print(f"\r[DONE] 分析完成: 成功 {success}, 失败 {failed}, 共 {len(materials)} 条")


if __name__ == "__main__":
    main()
