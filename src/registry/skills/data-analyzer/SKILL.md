---
name: data-analyzer
description: 数据分析执行，提取数据特征
allowed-tools: []
context: inline
---

# Data Analyzer

Extract structured features from data summaries to inform statistical analysis recommendations.

# Data Analyzer

Extract structured features from data summaries to inform statistical analysis recommendations.

## When to Use

Use this skill when:
- User provides a data summary in skimr format
- User shares output from R's `skimr` package or similar summary statistics
- User describes their dataset structure (variables, sample size, etc.)
- User asks about analyzing their data without providing specific analysis goals

## Data Summary Formats

### Skimr Format (Most Common)
```
Skim summary statistics
 n obs: 150
 n variables: 8

Variable type: numeric
  min mean max sd
  age 18 45.2 89 15.3
  bmi 18.5 25.4 45.2 4.2

Variable type: categorical
  n_missing top_counts
  treatment 0 group A: 75, group B: 75
```

### Alternative Formats
- Standard summary statistics (mean, SD, min, max)
- Data dictionary descriptions
- Variable lists with types

## Extracted Features

The analysis extracts:

1. **Sample Size** (`n obs`, `sample size`, `n =`)
   - Required for power analysis and method selection

2. **Variable Types**
   - `numeric`: Continuous variables (age, weight, scores)
   - `categorical`: Factor/character variables (group, category)
   - `binary`: Yes/no, true/false variables
   - `ordinal`: Ordered categories

3. **Grouping Variables**
   - Variables that define comparison groups
   - Keywords: group, treatment, condition, arm, cohort

4. **Study Design**
   - `randomized_controlled_trial`: RCT, randomized, controlled trial
   - `cohort_study`: Cohort, longitudinal, prospective
   - `case_control`: Case-control, case control
   - `cross_sectional`: Cross-sectional, survey
   - `meta_analysis`: Meta-analysis, systematic review

5. **Statistical Characteristics**
   - Mean, SD, min, max for numeric variables
   - Counts for categorical variables

6. **Missing Data Patterns**
   - Detected missing value counts
   - Variables with NAs

## Using the Script

To analyze data programmatically:

```bash
python src/registry/skills/data_analyzer/scripts/analyze.py --data-summary "<summary_text>"
```

Or use as a module:

```python
from src.registry.skills.data_analyzer.scripts.analyze import analyze_data

result = analyze_data(data_summary_text)
# Returns: dict with sample_size, variable_types, grouping_variables, etc.
```

## Output Format

```json
{
  "sample_size": 150,
  "n_variables": 8,
  "variable_types": {
    "numeric": ["age", "bmi"],
    "categorical": ["treatment"],
    "binary": [],
    "ordinal": []
  },
  "grouping_variables": ["treatment"],
  "study_design": "randomized_controlled_trial",
  "missing_data": {"detected": false},
  "statistical_characteristics": {
    "mean": [45.2, 25.4],
    "sd": [15.3, 4.2]
  },
  "raw_variables": ["age", "bmi", "treatment"]
}
```

## Integration with Other Skills

This skill's output feeds into:
- **literature-matcher**: Uses data features to find matching methods
- **question-generator**: Uses missing features to generate clarification questions
- **pipeline-decision**: Uses completeness to determine if pipeline can be suggested
