---
name: data-analyzer
description: Intelligent data analysis tool for CSV/JSON files. Computes statistics, generates visualizations (violin plots, etc.), and performs exploratory data analysis. Use proactively when users provide data files or request data analysis.
allowed-tools: []
context: inline
execution:
  type: script
  handler: scripts/analyze.py
  entrypoint: main
  timeout: 60
---

# Data Analyzer

智能数据分析工具，支持描述性统计、分布可视化等分析。当用户提供数据文件或请求数据分析时，主动使用此技能。

## When Invoked

1. Identify the data file path from user request
2. Decide which action to use based on user's intent
3. Execute the appropriate action
4. Present results to user, especially `image_path` for visualizations

## Action Selection Guide

| User Request | Action | Tool | Example |
|--------------|--------|------|---------|
| "小提琴图"/"violin"/"分布图" | run | violin | `绘制小提琴图 iris.csv` |
| "描述性统计"/"统计量"/"均值" | run | descriptives | `计算统计量 iris.csv` |
| "箱线图"/"boxplot" | run | boxplot | `画箱线图 data.csv` |
| "分析这个数据"/"看看数据" | scan | - | `分析一下 iris.csv` |
| "有什么工具"/"能做什么" | list_tools | - | `有什么工具` |

**Critical Rule: When user explicitly requests a visualization or analysis type, execute the corresponding tool immediately. Do not just scan.**

## Available Actions

### Action: run - Execute analysis tool

```json
{"action": "run", "tool": "violin", "file_path": "path/to/data.csv"}
```

Available tools: `violin`, `descriptives`

### Action: scan - Scan data characteristics

```json
{"action": "scan", "file_path": "path/to/data.csv"}
```

Use when exploring unknown data or user's request is vague.

### Action: list_tools - List available tools

```json
{"action": "list_tools"}
```

## Tool Specifications

### descriptives - 描述性统计

Calculates mean, std, median, quartiles for numeric variables.

**When to use:**
- User requests statistics or summary
- Numerical data analysis needed
- Data quality check (identify outliers)

### violin - 小提琴图

Generates violin plot for distribution visualization.

**When to use:**
- User requests violin plot or distribution visualization
- Compare distributions across groups

**Result format:**
```json
{
  "tool": "violin",
  "result": {
    "image_path": "/tmp/data_analyzer_plots/violin_*.png"
  }
}
```

**Always inform user of the `image_path` location.**

## Supported Data Formats

- CSV files (.csv)
- JSON files (.json) - arrays or objects with data/records field
- JSON Lines files (.jsonl)

## Important Rules

1. **Do not output Python code** - use built-in tools directly
2. **Execute immediately when request is clear** - don't scan first if user specifies the analysis
3. **Report image_path** - always tell users where generated images are saved
4. **Smart defaults** - tools auto-detect variables, no need to specify manually
