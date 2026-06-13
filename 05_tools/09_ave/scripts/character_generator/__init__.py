"""
角色生成器包 — Character Generator Package

提供从粗方向到完整角色变体素材的全流程：
  - DirectionExpander      方向扩展（粗方向→详细描述）
  - AttributeExtractor     属性提取（自然语言→结构化属性）
  - PromptAssembler        提示词组装（结构化属性→Kling/即梦提示词）
  - VariantGenerator       变体生成（Kling API 批量生成多角度/表情）
  - AssetRegistrar         资产注册（注册到 registry.yaml + 知识库）
  - CharacterGenerationPipeline  全流程编排器
"""
