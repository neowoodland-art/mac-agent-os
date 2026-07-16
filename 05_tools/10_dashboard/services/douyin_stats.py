"""
douyin_stats.py — 抖音视频数据采集器（v3）
 
适配层：调用 MediaCrawler 风格适配器
"""
import asyncio, json, logging, os, re
from pathlib import Path

logger = logging.getLogger("dashboard.douyin_stats")

# 导入 MediaCrawler 适配器
from services.mediacrawler_adapter import get_video_data as _mc_get_video_data


async def get_video_data(url: str) -> dict:
    """统一入口：传入抖音视频 URL，返回完整数据
    
    委托给 MediaCrawler 适配器处理。
    """
    return await _mc_get_video_data(url)
