---
name: translation
description: 中英文互译技能，支持多领域文本翻译
allowed-tools: []
context: inline
execution:
  type: script
  handler: scripts/translate.py
  entrypoint: translate
  timeout: 30
---

# Translation Skill

中英文互译，支持多种文本类型。

## When to Use

Use this skill when:
- User asks to translate text between Chinese and English
- User asks "用英文怎么说"、"翻译一下"、"这句话什么意思"
- User provides text with translation intent

## Input Requirements

Required:
- `text`: 要翻译的文本
- `source_lang`: 源语言 ("zh" for Chinese, "en" for English, "auto" for auto-detect)
- `target_lang`: 目标语言 ("zh" for Chinese, "en" for English)

## Output Format

```json
{
  "success": true,
  "original": "原始文本",
  "source_lang": "zh",
  "target_lang": "en",
  "translation": "Translated text",
  "alternatives": ["可选译文2", "可选译文3"]
}
```

## Supported Languages

- `zh`: 中文
- `en`: 英语

## Examples

```python
from translate import translate

# 中译英
result = translate(text="你好，世界", source_lang="zh", target_lang="en")
# {"success": true, "translation": "Hello, World", ...}

# 英译中
result = translate(text="Good morning", source_lang="en", target_lang="zh")
# {"success": true, "translation": "早上好", ...}
```
