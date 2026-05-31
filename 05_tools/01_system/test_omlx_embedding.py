#!/usr/bin/env python3
"""
测试 oMLX embedding API 是否在自动化环境中正常工作
"""

import requests
import json
import sys

def test_embedding_api():
    """测试 embedding API"""
    url = "http://localhost:8000/v1/embeddings"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer omlx"
    }
    data = {
        "model": "Qwen3-Embedding-0.6B",
        "input": ["测试文本：这是用于验证 oMLX embedding API 是否正常工作的测试文本。"]
    }
    
    try:
        print("测试 oMLX embedding API...")
        print(f"URL: {url}")
        print(f"Headers: {headers}")
        print(f"Data: {json.dumps(data, ensure_ascii=False)}")
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API 调用成功！")
            print(f"返回数据: {json.dumps(result, ensure_ascii=False)[:200]}...")
            
            # 检查向量维度
            if "data" in result and len(result["data"]) > 0:
                embedding = result["data"][0]["embedding"]
                print(f"向量维度: {len(embedding)} (应为 1024)")
                if len(embedding) == 1024:
                    print("✅ 向量维度正确！")
                else:
                    print(f"⚠️ 向量维度异常: {len(embedding)}")
            
            return True
        else:
            print(f"❌ API 调用失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到 oMLX API (ConnectionError)")
        print("请确保 oMLX 应用正在运行，端口 8000 可访问")
        return False
    except requests.exceptions.Timeout:
        print("❌ API 请求超时")
        return False
    except Exception as e:
        print(f"❌ 未知错误: {type(e).__name__}: {e}")
        return False

def test_chat_api():
    """测试 chat completions API"""
    url = "http://localhost:8000/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer omlx"
    }
    data = {
        "model": "Qwen3-8B-MLX-4bit",
        "messages": [{"role": "user", "content": "你好，请回复'测试成功'"}],
        "stream": False,
        "temperature": 0.1
    }
    
    try:
        print("\n测试 oMLX chat completions API...")
        response = requests.post(url, headers=headers, json=data, timeout=60)
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Chat API 调用成功！")
            if "choices" in result and len(result["choices"]) > 0:
                message = result["choices"][0]["message"]["content"]
                print(f"回复内容: {message}")
            return True
        else:
            print(f"❌ Chat API 调用失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Chat API 错误: {type(e).__name__}: {e}")
        return False

def test_models_api():
    """测试 models API"""
    url = "http://localhost:8000/v1/models"
    headers = {"Authorization": "Bearer omlx"}
    
    try:
        print("\n测试 oMLX models API...")
        response = requests.get(url, headers=headers, timeout=10)
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Models API 调用成功！")
            print(f"可用模型: {json.dumps(result, ensure_ascii=False)}")
            return True
        else:
            print(f"❌ Models API 调用失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Models API 错误: {type(e).__name__}: {e}")
        return False

def main():
    print("=" * 60)
    print("oMLX API 测试脚本")
    print("=" * 60)
    
    # 测试 models API
    models_ok = test_models_api()
    
    # 测试 embedding API
    embedding_ok = test_embedding_api()
    
    # 测试 chat API
    chat_ok = test_chat_api()
    
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print(f"  Models API: {'✅ 正常' if models_ok else '❌ 异常'}")
    print(f"  Embedding API: {'✅ 正常' if embedding_ok else '❌ 异常'}")
    print(f"  Chat API: {'✅ 正常' if chat_ok else '❌ 异常'}")
    print("=" * 60)
    
    # 关键检查：embedding API 是否正常
    if embedding_ok:
        print("\n✅ 关键依赖：embedding API 正常，向量化功能可用")
        print("  这意味着 daily_digest.py 的向量化步骤可以正常工作")
    else:
        print("\n❌ 关键依赖：embedding API 异常，向量化功能不可用")
        print("  这会影响记忆系统的语义检索能力")
    
    if not chat_ok:
        print("\n⚠️  Chat API 异常，但这不是关键依赖")
        print("  inbox_refine.py 的智能分类功能会降级到启发式规则")

if __name__ == "__main__":
    main()