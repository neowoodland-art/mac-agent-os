# 知识属性分类表

> 本表定义了知识的 nature 属性类型，决定了知识卡片在知识库中的物理位置。

## 属性类型

| nature 值 | 中文名称 | 说明 | 目标目录 | 可信度权重 |
|---|---|---|---|---|
| fact | 事实 | 已验证的客观事实 | 30_facts/ | 1.0 |
| method | 方法 | 可操作的步骤、教程、最佳实践 | 20_methods/ | 1.0 |
| concept | 概念 | 原子概念、知识卡片 | 10_concepts/ | 0.8 |
| regulation | 规章制度 | 法律、法规、组织制度 | 30_facts/ | 1.0 |
| reference | 参考资料 | 论文、文档、外部资料 | 40_references/ | 0.7 |
| data | 数据 | 测试数据、基准测试结果 | 30_facts/ | 0.9 |
| opinion | 观点 | 主观看法、推测、未验证想法 | 60_opinions/ | 0.5 |
| quote | 引用 | 他人原话、经典语录 | 60_opinions/ | 0.6 |
| axiom | 公理 | 公认的基础原理，无需证明 | 10_concepts/ | 1.0 |

## 分类决策树

```
这段内容是在描述"世界是什么样"还是在说"应该怎么做"？
├── "是什么" → 可能是 fact/opinion/quote/data/reference/axiom
│   ├── 有实验数据/论文支持 → fact (confidence: 0.8+)
│   ├── 是作者的个人看法 → opinion (confidence: 0.4-0.6)
│   ├── 是引用的他人原话 → quote (confidence: 标注来源可信度)
│   ├── 是公认无需证明的原理 → axiom (confidence: 0.95+)
│   ├── 是链接/文献/资料 → reference (confidence: 0.7)
│   └── 是测试数据/基准结果 → data (confidence: 0.9)
└── "怎么做" → 可能是 method/regulation
    ├── 有明确法律/组织强制力 → regulation (confidence: 1.0)
    └── 是可操作的步骤/教程 → method (confidence: 1.0)
```

## 属性变更规则

- opinion → fact：观点被验证为事实时，confidence 提升，文件移动到 30_facts/
- fact → opinion：事实被推翻时，confidence 降低，文件移动到 60_opinions/
- 所有属性变更由 kb_manager reclassify 自动处理，同时更新内链
