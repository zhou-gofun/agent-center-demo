---
name: question-generator
description: 问题生成，基于数据特征生成追问
allowed-tools: []
context: inline
---

# Question Generator

Generate relevant follow-up questions to clarify analysis requirements and gather missing information.

# Question Generator

Generate relevant follow-up questions to clarify analysis requirements and gather missing information.

## When to Use

Use this skill when:
- Data features are incomplete or ambiguous
- Multiple analysis approaches are possible
- Literature match confidence is moderate
- User goals need clarification

## Question Categories

### 1. Data Clarification
Questions about the dataset structure and characteristics.

**Trigger conditions:**
- Sample size is unknown
- No grouping variables identified
- Study design is unknown

**Example questions:**
- "What is the sample size of your dataset?"
- "Are there any grouping or comparison variables in your data?"
- "What type of study design does this data come from?"

### 2. Analysis Goals
Questions about research objectives and hypotheses.

**Trigger conditions:**
- Always ask (primary research question)
- Grouping variables present (comparison vs relationship)
- Multiple numeric variables (outcome identification)

**Example questions:**
- "What is your primary research question or hypothesis?"
- "Do you want to compare groups or examine relationships between variables?"
- "Which variables are your primary outcomes of interest?"

### 3. Method Preferences
Questions about statistical method preferences.

**Trigger conditions:**
- Multiple methods recommended (>2)
- Small sample size (<50)
- Conflicting method options (t-test vs ANOVA)

**Example questions:**
- "Do you have preferences for specific statistical methods?"
- "Would you consider non-parametric methods given the small sample size?"
- "Do you have exactly two groups to compare, or more than two?"

### 4. Validation
Questions about assumptions and constraints.

**Trigger conditions:**
- High literature match confidence
- Specific methods identified

**Example questions:**
- "Would you like to see the specific methods used in similar studies?"

## Question Priority

| Priority | When to Use | Examples |
|----------|-------------|----------|
| High | Missing critical info, multiple paths | Sample size, research hypothesis, group definition |
| Medium | Moderate gaps, optional preferences | Study design, method preferences |
| Low | Nice-to-have information | Literature examples, specific method details |

## Using the Script

```bash
python src/registry/skills/question_generator/scripts/generate.py \
  --data-features '{"sample_size": null, "grouping_variables": []}' \
  --literature-matches '{"confidence": 0.5}'
```

Or as a module:

```python
from src.registry.skills.question_generator.scripts.generate import generate_questions

result = generate_questions(
    data_features={"sample_size": 150, "grouping_variables": ["treatment"]},
    literature_matches={"confidence": 0.8, "recommended_methods": ["t_test", "anova"]},
    query="compare treatment groups"
)
```

## Output Format

```json
{
  "questions": [
    {
      "question": "What is your primary research hypothesis?",
      "rationale": "Understanding the hypothesis helps select the most appropriate statistical test.",
      "category": "analysis_goals",
      "priority": "high"
    },
    {
      "question": "Do you have exactly two groups to compare, or more than two?",
      "rationale": "This determines whether a t-test or ANOVA is more appropriate.",
      "category": "method_preferences",
      "priority": "high"
    }
  ]
}
```

## Integration

This skill uses:
- **data-analyzer**: For data feature information
- **literature-matcher**: For method recommendations

This skill feeds into:
- **pipeline-decision**: Uses high-priority questions to determine if more info is needed
