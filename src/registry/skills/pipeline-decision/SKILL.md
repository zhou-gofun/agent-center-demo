---
name: pipeline-decision
description: 流程决策，决定是否建议生成分析流程
allowed-tools: []
context: inline
execution:
  type: script
  handler: scripts/decide.py
  entrypoint: make_decision
  timeout: 30
---

# Pipeline Decision

Decide whether to suggest pipeline composition, continue asking questions, or provide a direct answer.

# Pipeline Decision

Decide whether to suggest pipeline composition, continue asking questions, or provide a direct answer.

## When to Use

Use this skill after:
- Data features have been extracted
- Literature matching has been performed
- Questions have been generated (if needed)

## Decision Types

### 1. Suggest Pipeline

Recommend creating a statistical analysis pipeline.

**Conditions:**
- Literature match confidence ≥ 0.7
- No critical missing information
- Sufficient data features present

**Example message:**
> "Based on your RCT study with 150 samples and grouping variables, I found relevant analysis methods like t-test and ANOVA. Would you like me to create a statistical analysis pipeline for you?"

**What happens next:**
- User confirms → Call pipeline_agent
- User declines → Provide alternative suggestions

### 2. Continue Questions

Ask for more information before proceeding.

**Conditions:**
- High-priority questions unanswered
- Critical information missing (sample size, grouping variables)
- Literature match confidence < 0.4

**Example message:**
> "To provide the best analysis recommendation, I need a bit more information. Could you help me understand: sample size, grouping variables?"

**What happens next:**
- Present 1-2 high-priority questions
- Re-evaluate after answers

### 3. Direct Answer

Provide a helpful response without pipeline creation.

**Conditions:**
- Simple informational query
- No data analysis needed
- Quick answer sufficient

**Example message:**
> "For comparing two groups, common methods include t-test (parametric) and Mann-Whitney U test (non-parametric)."

## Critical Information

The following are considered critical for pipeline creation:
- `sample_size`: Required for method selection
- `grouping_variables`: Required for comparison tests
- `outcome_variables`: Required for analysis planning

## Sufficient Information Indicators

Pipeline can be suggested when:
- Has grouping variables OR recommended methods
- Has sample size > 0
- Has variables defined (numeric/categorical/binary)

## Confidence Thresholds

| Threshold | Action |
|-----------|--------|
| ≥ 0.7 | Suggest pipeline (if no missing info) |
| 0.4 - 0.7 | Consider questions first |
| < 0.4 | Need more information |

## Using the Script

```bash
python src/registry/skills/pipeline_decision/scripts/decide.py \
  --data-features '{"sample_size": 150, "grouping_variables": ["treatment"]}' \
  --literature-matches '{"confidence": 0.85, "recommended_methods": ["t_test"]}' \
  --questions '[{"question": "...", "priority": "high"}]'
```

Or as a module:

```python
from registry.skills.pipeline_decision.scripts.decide import make_decision

result = make_decision(
    data_features={"sample_size": 150, "grouping_variables": ["treatment"]},
    literature_matches={"confidence": 0.85, "recommended_methods": ["t_test"]},
    generated_questions=[{"question": "...", "priority": "high"}]
)
```

## Output Format

```json
{
  "decision": "suggest_pipeline",
  "confidence": 0.85,
  "reasoning": "High literature match confidence (0.85) with sufficient data features and recommended methods available.",
  "message": "Based on your data characteristics and matched literature, I can help you create a statistical analysis pipeline. Would you like me to proceed?",
  "suggested_methods": ["t_test", "anova"],
  "missing_information": []
}
```

## Decision Flow

```
┌─────────────────────────────────────┐
│     Input: data_features,           │
│     literature_matches, questions    │
└─────────────────┬───────────────────┘
                  │
                  ▼
        ┌─────────────────┐
        │ Check missing   │──── Critical info missing?
        │ information     │
        └────────┬────────┘
                 │ No
                 ▼
        ┌─────────────────┐
        │ Check confidence │──── < 0.4?
        └────────┬────────┘
                 │ Yes
                 ▼
        ┌─────────────────┐
        │ Check high      │──── High priority questions?
        │ priority Qs     │
        └────────┬────────┘
                 │ No
                 ▼
        ┌─────────────────┐
        │ Check sufficient │──── Has grouping/methods?
        │ information     │
        └────────┬────────┘
                 │ Yes
                 ▼
    ┌────────────────────────┐
    │ SUGGEST PIPELINE       │
    └────────────────────────┘
```

## Integration

This skill uses:
- **data-analyzer**: For data feature completeness
- **literature-matcher**: For confidence scores
- **question-generator**: For priority assessment

This skill determines:
- Whether to call pipeline-agent
- Whether to ask more questions
- Whether to provide direct answer
