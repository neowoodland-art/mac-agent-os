"""
AVE asset_manager — 素材资产管理包

提供素材索引、缓存管理、标签搜索三大能力。

模块:
  index.py   — AssetIndex: 扫描目录、提取元数据、入库 SQLite
  cache.py   — CacheManager: 增量扫描、缓存清理、孤立文件回收
  tags.py    — AssetSearch: 自动标签、模糊搜索、CLI 查询

依赖:
  - lib/dashboard.py (assets 表 schema 已存在)
  - ffprobe (FFmpeg, 用于提取视频元数据)
"""
