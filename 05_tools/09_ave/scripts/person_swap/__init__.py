"""
person_swap — 人物置换(全身身份替换)视频生成模块

基于阿里云百炼 Wan2.2-Animate (图+原视频 → 保留动作的新人物视频)

模块组成:
  api.py        — 百炼异步任务封装(上传/提交/轮询/下载) + 账号探活
  preprocess.py — ffmpeg 素材合规化(转码/竖屏裁切/限长/参考图归一化)
  service.py    — 任务队列(SQLite + 后台 worker) + 重试 + 费用护栏

运行数据(程序自建, 不入 git):
  agent-local/runtime/person_swap/{tasks.db, uploads/, outputs/}

⚠️ 账号欠费(Arrearage)会阻塞生成 — 页面/api 会给出明确提示, 处理后无需改代码。
⚠️ 模型 id 与 input 字段名: 配置 person_swap.model / input_image_field / input_video_field,
   待账号开通后在百炼控制台模型广场核对校准。
"""
__version__ = "0.1.0"
