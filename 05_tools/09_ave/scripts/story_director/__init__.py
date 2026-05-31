"""
AVE story_director — 角色叙事策略
====================================

职责:
  将导演脚本分解为多个场景，跨场景维持角色一致性，
  批量调用 Kling 图生视频生成各场景，拼接为完整叙事视频。

模块:
  scene_planner.py    剧本→N个场景 + 每场景 Prompt
  temporal_bridge.py  场景间过渡桥接（末帧→首帧条件）
  batch_generator.py  批量 Kling 生成（固定 seed + 角色描述块）
"""
