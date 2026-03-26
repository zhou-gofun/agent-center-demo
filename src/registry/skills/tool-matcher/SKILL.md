---
name: tool-matcher
description: 根据分析需求匹配最合适的统计工具
allowed-tools: [Read, Grep]
context: inline
---

# Tool Matcher

Match statistical analysis tools to user requirements based on study design, variables, and analysis goals.

# Tool Matcher

Match statistical analysis tools to user requirements based on study design, variables, and analysis goals.

## When to Use

Use this skill when:
- User asks "what tool should I use for..."
- User describes their analysis needs
- Finding tools for specific statistical tests
- Discovering tools for research designs

## Input Requirements

Required:
- `query`: User's analysis question or requirement

Optional:
- `top_k`: Number of results to return (default: 10)
- `use_vector`: Whether to use vector search (default: False - uses keyword matching)

## Search Methods

### Keyword Matching (Default)
Faster, deterministic matching based on:
- Tool names
- Keywords
- Applications
- Descriptions

**Scoring:**
- Tool name match: +3.0
- Keyword match: +2.0
- Application match: +1.0
- Description match: +0.5

### Vector Search (Optional)
Semantic meaning-based matching using embeddings.
More flexible but slower.

## Common Search Terms

| Category | Keywords |
|----------|----------|
| Descriptive Statistics | 描述性统计, descriptive, 均值, 标准差, 中位数 |
| Group Comparison | 组间比较, 比较, 差异, group comparison, t检验 |
| ANOVA | 方差分析, anova, 多组比较 |
| Chi-square | 卡方, chi-square, 分类 |
| Regression | 回归, regression, 预测 |
| Correlation | 相关, correlation, 关系 |
| Survival Analysis | 生存, survival, kaplan-meier |
| Visualization | 图, plot, 可视化, 图表 |
| Normality Test | 正态, normality |

## Using the Script

```bash
python src/registry/skills/tool_matcher/scripts/match.py \
  --query "compare two groups" \
  --top-k 5
```

Or as a module:

```python
from src.registry.skills.tool_matcher.scripts.match import match_tools

result = match_tools(
    query="compare treatment groups",
    top_k=5
)
```

## Output Format

```json
{
  "matched_tools": [
    {
      "toolid": 123,
      "toolname": "Independent t-test",
      "idname": "t_test_independent",
      "relevance_score": 0.9,
      "match_reason": "关键词匹配: compare, group, t检验",
      "keywords": "t-test, group comparison",
      "applications": "Compare means between two groups",
      "conditions": "Two independent groups, continuous outcome"
    }
  ],
  "requirements_analysis": {
    "query": "compare two groups",
    "found_tools": 5,
    "search_method": "keyword_matching"
  }
}
```

## Relevance Scores

- **≥ 0.8**: High relevance - direct match to requirements
- **0.5 - 0.8**: Moderate relevance - related tools
- **< 0.5**: Low relevance - may not fit requirements

## Integration

This skill is used by:
- **pipeline-agent**: For finding tools to include in pipelines
- **conversation-orchestrator-agent**: For suggesting tools to users

## Technical Notes

- Uses assembly tools data loader
- Keyword matching is default (faster, no ONNX dependency)
- Vector search available but disabled by default
- Chinese and English term support
