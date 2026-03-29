---
name: literature-matcher
description: 文献匹配，基于数据特征推荐统计方法
allowed-tools: [Read]
context: inline
execution:
  type: script
  handler: scripts/match.py
  entrypoint: match_literature
  timeout: 30
---

# Literature Matcher

Match medical literature to data characteristics and recommend evidence-based statistical analysis methods.

# Literature Matcher

Match medical literature to data characteristics and recommend evidence-based statistical analysis methods.

## When to Use

Use this skill when:
- User has data features extracted and needs method recommendations
- User asks "what statistical methods should I use?"
- User wants evidence-based analysis approaches
- Literature-backed method selection is needed

## Database Location

The skill searches for the literature database in these locations:
- `pmcids_list.get.methods.filter(1).xlsx`
- `data/pmcids_list.get.methods.filter(1).xlsx`
- `src/data/pmcids_list.get.methods.filter(1).xlsx`
- `database/pmcids_list.get.methods.filter(1).xlsx`

If the database is not found, the skill falls back to keyword-based method matching.

## Input Requirements

Required:
- `data_features`: Dictionary with extracted data characteristics

Optional:
- `query`: User's analysis question or goal

### Data Features Structure

```json
{
  "sample_size": 150,
  "variable_types": {
    "numeric": ["age", "bmi"],
    "categorical": ["treatment"]
  },
  "grouping_variables": ["treatment"],
  "study_design": "randomized_controlled_trial"
}
```

## Method Mapping

### By Study Design

| Study Design | Recommended Methods |
|--------------|---------------------|
| RCT | t-test, ANOVA, ANCOVA, mixed models |
| Cohort | Survival analysis, regression, logistic |
| Case-control | Chi-square, Fisher's exact, logistic |
| Cross-sectional | Chi-square, correlation, regression |
| Meta-analysis | MCMC, regression |

### By Variable Characteristics

| Characteristic | Methods |
|---------------|---------|
| Numeric + grouping | t-test, ANOVA, Mann-Whitney |
| Categorical + grouping | Chi-square, Fisher's exact |
| Small sample (<30) | Mann-Whitney, Wilcoxon |
| Large sample | Parametric tests |

## Using the Script

```bash
python src/registry/skills/literature_matcher/scripts/match.py \
  --data-features '{"sample_size": 150, "study_design": "randomized_controlled_trial"}' \
  --query "compare treatment groups"
```

Or as a module:

```python
from registry.skills.literature_matcher.scripts.match import match_literature

result = match_literature(
    data_features={"sample_size": 150, "study_design": "rct"},
    query="compare groups"
)
```

## Output Format

```json
{
  "matches": [
    {
      "pmcid": "PMC1234567",
      "title": "Statistical methods for RCTs",
      "relevance_score": 0.85,
      "methods": ["t_test", "ancova"],
      "study_design": "randomized_controlled_trial",
      "abstract": "..."
    }
  ],
  "recommended_methods": ["t_test", "anova", "ancova"],
  "confidence": 0.85,
  "total_searched": 100
}
```

## Confidence Thresholds

- **≥ 0.7**: High confidence - suitable for pipeline recommendation
- **0.4 - 0.7**: Moderate confidence - consider asking clarifying questions
- **< 0.4**: Low confidence - need more information

## Integration

This skill uses:
- **data-analyzer**: For input data features

This skill feeds into:
- **question-generator**: Method-specific questions
- **pipeline-decision**: Confidence-based decision making
