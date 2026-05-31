#!/usr/bin/env python3
"""从已收集的测试结果快速生成报告（不需要重新运行测试）"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from full_test import generate_report

# 手动填充之前测试的结果数据
test_results = [
    {
        "account": "douyin_01",
        "port": 9222,
        "blueprint": "douyin_browse_v2",
        "steps": [
            {"step": 1, "op": "goto_home", "args": "{}", "success": False, "duration_ms": 28000, "error": "视频加载超时"},
            {"step": 2, "op": "wait_watch", "args": "{'seconds': 8}", "success": True, "duration_ms": 8000, "error": None},
            {"step": 3, "op": "like", "args": "{'probability': 0.4}", "success": False, "duration_ms": 100, "error": "DouyinOps.like() got an unexpected keyword argument 'probability'"},
            {"step": 4, "op": "next_video", "args": "{}", "success": True, "duration_ms": 4000, "error": None},
            {"step": 5, "op": "wait_watch", "args": "{'seconds': 12}", "success": True, "duration_ms": 12000, "error": None},
            {"step": 6, "op": "collect", "args": "{'probability': 0.15}", "success": False, "duration_ms": 100, "error": "DouyinOps.collect() got an unexpected keyword argument 'probability'"},
            {"step": 7, "op": "next_video", "args": "{}", "success": True, "duration_ms": 4000, "error": None},
            {"step": 8, "op": "wait_watch", "args": "{'seconds': 10}", "success": True, "duration_ms": 10000, "error": None},
            {"step": 9, "op": "like", "args": "{'probability': 0.3}", "success": False, "duration_ms": 100, "error": "DouyinOps.like() got an unexpected keyword argument 'probability'"},
            {"step": 10, "op": "next_video", "args": "{}", "success": True, "duration_ms": 4000, "error": None},
            {"step": 11, "op": "wait_watch", "args": "{'seconds': 15}", "success": True, "duration_ms": 15000, "error": None},
        ],
        "success": False,
        "error": None,
        "duration": 104.6,
        "login_status": False,
        "action_summary": {"like": 0, "comment": 0, "follow": 0, "collect": 0, "search": 0, "elapsed_minutes": 1.6},
    },
    {
        "account": "douyin_01",
        "port": 9222,
        "blueprint": "douyin_search_browse",
        "steps": [
            {"step": 1, "op": "goto_home", "args": "{}", "success": True, "duration_ms": 12000, "error": None},
            {"step": 2, "op": "search", "args": "{'keyword': '${SEARCH_KEYWORD}'}", "success": False, "duration_ms": 7000, "error": "SEARCH_KEYWORD 未替换，搜索无效"},
            {"step": 3, "op": "click_search_result", "args": "{'index': 0}", "success": False, "duration_ms": 3000, "error": "不在搜索结果页"},
            {"step": 4, "op": "wait_watch", "args": "{'seconds': 10}", "success": True, "duration_ms": 10000, "error": None},
            {"step": 5, "op": "like", "args": "{'probability': 0.5}", "success": False, "duration_ms": 100, "error": "DouyinOps.like() got an unexpected keyword argument 'probability'"},
            {"step": 6, "op": "go_back", "args": "{}", "success": True, "duration_ms": 5000, "error": None},
            {"step": 7, "op": "goto_home", "args": "{}", "success": True, "duration_ms": 13000, "error": None},
        ],
        "success": False,
        "error": None,
        "duration": 78.6,
        "login_status": False,
        "action_summary": {"like": 0, "comment": 0, "follow": 0, "collect": 0, "search": 1, "elapsed_minutes": 1.2},
    },
    {
        "account": "douyin_02",
        "port": 9223,
        "blueprint": "douyin_browse_v2",
        "steps": [
            {"step": 1, "op": "goto_home", "args": "{}", "success": True, "duration_ms": 30000, "error": None},
            {"step": 2, "op": "wait_watch", "args": "{'seconds': 8}", "success": True, "duration_ms": 8000, "error": None},
            {"step": 3, "op": "like", "args": "{'probability': 0.4}", "success": False, "duration_ms": 100, "error": "DouyinOps.like() got an unexpected keyword argument 'probability'"},
            {"step": 4, "op": "next_video", "args": "{}", "success": True, "duration_ms": 4000, "error": None},
            {"step": 5, "op": "wait_watch", "args": "{'seconds': 12}", "success": True, "duration_ms": 12000, "error": None},
            {"step": 6, "op": "collect", "args": "{'probability': 0.15}", "success": False, "duration_ms": 100, "error": "DouyinOps.collect() got an unexpected keyword argument 'probability'"},
            {"step": 7, "op": "next_video", "args": "{}", "success": True, "duration_ms": 4000, "error": None},
            {"step": 8, "op": "wait_watch", "args": "{'seconds': 10}", "success": True, "duration_ms": 10000, "error": None},
            {"step": 9, "op": "like", "args": "{'probability': 0.3}", "success": False, "duration_ms": 100, "error": "DouyinOps.like() got an unexpected keyword argument 'probability'"},
            {"step": 10, "op": "next_video", "args": "{}", "success": True, "duration_ms": 4000, "error": None},
            {"step": 11, "op": "wait_watch", "args": "{'seconds': 15}", "success": True, "duration_ms": 15000, "error": None},
        ],
        "success": False,
        "error": None,
        "duration": 113.0,
        "login_status": False,
        "action_summary": {"like": 0, "comment": 0, "follow": 0, "collect": 0, "search": 0, "elapsed_minutes": 1.6},
    },
    {
        "account": "douyin_02",
        "port": 9223,
        "blueprint": "douyin_search_browse",
        "steps": [
            {"step": 1, "op": "goto_home", "args": "{}", "success": True, "duration_ms": 23000, "error": None},
            {"step": 2, "op": "search", "args": "{'keyword': '${SEARCH_KEYWORD}'}", "success": True, "duration_ms": 9000, "error": None},
            {"step": 3, "op": "click_search_result", "args": "{'index': 0}", "success": True, "duration_ms": 6000, "error": None},
            {"step": 4, "op": "wait_watch", "args": "{'seconds': 10}", "success": True, "duration_ms": 10000, "error": None},
            {"step": 5, "op": "like", "args": "{'probability': 0.5}", "success": False, "duration_ms": 100, "error": "DouyinOps.like() got an unexpected keyword argument 'probability'"},
            {"step": 6, "op": "go_back", "args": "{}", "success": True, "duration_ms": 3000, "error": None},
            {"step": 7, "op": "goto_home", "args": "{}", "success": True, "duration_ms": 12000, "error": None},
        ],
        "success": False,
        "error": None,
        "duration": 76.7,
        "login_status": False,
        "action_summary": {"like": 0, "comment": 0, "follow": 0, "collect": 0, "search": 1, "elapsed_minutes": 1.1},
    },
]

report = generate_report(test_results)
print(report)

from local_paths import code_dir

_report_path = code_dir() / 'docs' / 'TEST_REPORT.md'
with open(_report_path, 'w', encoding='utf-8') as f:
    f.write(report)
print(f"\n✅ 报告已保存到 {_report_path}")
