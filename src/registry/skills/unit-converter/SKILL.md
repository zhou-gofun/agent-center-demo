---
name: unit-converter
description: 常用单位换算技能，支持长度、温度、重量、货币等换算
allowed-tools: []
context: inline
execution:
  type: script
  handler: scripts/convert.py
  entrypoint: convert
  timeout: 30
---

# Unit Converter Skill

常用单位之间的换算。

## When to Use

Use this skill when:
- User asks to convert between units (e.g., "100 USD to CNY", "37°C to °F")
- User asks "等于多少"、"换算"、"convert"

## Input Requirements

Required:
- `value`: 数值（数字）
- `from_unit`: 源单位
- `to_unit`: 目标单位

Optional:
- `category`: 单位类别 ("temperature", "length", "weight", "currency"), auto-detected if not provided

## Supported Conversions

### Temperature (温度)
| from | to | Example |
|------|-----|---------|
| c | f | 100c → 212f |
| f | c | 32f → 0c |
| c | k | 0c → 273.15k |
| f | k | 32f → 273.15k |

### Length (长度)
| Units |
|-------|
| m, cm, mm, km |
| in (英寸), ft (英尺), yd (码), mi (英里) |

### Weight (重量)
| Units |
|-------|
| kg, g, mg |
| lb (磅), oz (盎司) |

### Currency (货币)
| Units |
|-------|
| USD, CNY, EUR, GBP, JPY |

## Output Format

```json
{
  "success": true,
  "input": {"value": 100, "from_unit": "c", "to_unit": "f"},
  "output": {"value": 212, "unit": "f"},
  "formula": "°F = °C × 9/5 + 32 = 100 × 9/5 + 32 = 212"
}
```

## Examples

```python
from convert import convert

# 温度换算
result = convert(value=100, from_unit="c", to_unit="f")
# {"success": true, "output": {"value": 212, "unit": "f"}, "formula": "..."}

# 长度换算
result = convert(value=1, from_unit="km", to_unit="mi")
# {"success": true, "output": {"value": 0.621, "unit": "mi"}, ...}

# 货币换算
result = convert(value=100, from_unit="USD", to_unit="CNY")
```
