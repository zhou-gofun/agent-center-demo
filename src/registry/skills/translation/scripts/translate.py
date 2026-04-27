#!/usr/bin/env python3
"""
Translation Script

Simple Chinese-English translation without external API dependencies.
Uses rule-based approach for demo purposes.
"""

import json
import sys
import os
import re
from typing import Dict, Any, Optional, List

# Simple dictionary-based translation for demonstration
# In production, this would call an LLM or translation API

# Common phrases dictionary
DICT_ZH_TO_EN = {
    "你好": "Hello",
    "世界": "World",
    "早上好": "Good morning",
    "晚上好": "Good evening",
    "再见": "Goodbye",
    "谢谢": "Thank you",
    "对不起": "Sorry",
    "请": "Please",
    "是的": "Yes",
    "不是": "No",
    "我": "I",
    "你": "you",
    "他": "he",
    "她": "she",
    "它": "it",
    "我们": "we",
    "他们": "they",
    "这": "this",
    "那": "that",
    "是": "is",
    "在": "at/in",
    "有": "have",
    "没有": "don't have",
    "工作": "work",
    "学习": "study",
    "生活": "life",
    "时间": "time",
    "今天": "today",
    "明天": "tomorrow",
    "昨天": "yesterday",
    "天气": "weather",
    "怎么样": "how is",
    "怎么样？": "How is it going?",
    "很": "very",
    "好": "good",
    "很好": "very good",
    "不错": "not bad",
    "天气很好": "The weather is nice",
    "我很好": "I'm fine",
    "很高兴认识你": "Nice to meet you",
    "最近怎么样": "How have you been lately",
    "再见！": "Goodbye!",
    "谢谢你的帮助": "Thank you for your help",
    "对不起，我来晚了": "Sorry, I'm late",
}

DICT_EN_TO_ZH = {v: k for k, v in DICT_ZH_TO_EN.items()}

# Auto-detect language
def detect_language(text: str) -> str:
    """Simple language detection based on character ranges."""
    # Check for Chinese characters
    chinese_chars = len(re.findall(r'[一-鿿]', text))
    # Check for English words
    english_words = len(re.findall(r'[a-zA-Z]+', text))

    if chinese_chars > english_words:
        return "zh"
    elif english_words > 0:
        return "en"
    return "unknown"


def simple_translate(text: str, source_lang: str, target_lang: str) -> Dict[str, Any]:
    """
    Simple dictionary-based translation.
    For demo purposes - a real implementation would use LLM or translation API.
    """
    text = text.strip()

    if source_lang == target_lang:
        return {
            "success": True,
            "original": text,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "translation": text,
            "alternatives": [],
            "note": "Source and target language are the same"
        }

    result = None

    if source_lang == "zh" and target_lang == "en":
        # Try exact match first
        if text in DICT_ZH_TO_EN:
            result = DICT_ZH_TO_EN[text]
        else:
            # Try word by word
            words = text.split()
            translated_words = []
            for word in words:
                if word in DICT_ZH_TO_EN:
                    translated_words.append(DICT_ZH_TO_EN[word])
                else:
                    translated_words.append(f"[{word}]")

            # Check for punctuation
            punctuation = ""
            if translated_words and any(text.endswith(p) for p in "。！？,.!?"):
                punctuation = text[-1]
                translated_words.append(punctuation)

            result = " ".join(translated_words)

    elif source_lang == "en" and target_lang == "zh":
        # Try exact match first
        if text in DICT_EN_TO_ZH:
            result = DICT_EN_TO_ZH[text]
        else:
            # Try word by word
            words = text.replace(",", "").replace(".", "").split()
            translated_words = []
            for word in words:
                if word in DICT_EN_TO_ZH:
                    translated_words.append(DICT_EN_TO_ZH[word])
                else:
                    translated_words.append(f"[{word}]")

            punctuation = ""
            if any(text.endswith(p) for p in "。！？,.!?"):
                punctuation = "。" if not re.search(r'[.!?]', text[-1]) else ""

            result = "".join(translated_words) + punctuation

    if result is None:
        return {
            "success": False,
            "original": text,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "error": "Translation not found in dictionary",
            "suggestion": "Try simpler words or phrases"
        }

    return {
        "success": True,
        "original": text,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "translation": result,
        "alternatives": []
    }


def translate(text: str, source_lang: str = "auto", target_lang: str = "en") -> Dict[str, Any]:
    """
    Main translation function.

    Args:
        text: Text to translate
        source_lang: Source language ("zh", "en", "auto")
        target_lang: Target language ("zh", "en")

    Returns:
        Translation result dictionary
    """
    if not text:
        return {
            "success": False,
            "error": "Missing text parameter"
        }

    # Auto-detect source language if needed
    if source_lang == "auto":
        source_lang = detect_language(text)

    if source_lang not in ("zh", "en"):
        return {
            "success": False,
            "error": f"Unsupported source language: {source_lang}",
            "note": "Supported: zh (Chinese), en (English), auto (auto-detect)"
        }

    if target_lang not in ("zh", "en"):
        return {
            "success": False,
            "error": f"Unsupported target language: {target_lang}",
            "note": "Supported: zh (Chinese), en (English)"
        }

    return simple_translate(text, source_lang, target_lang)


def main():
    """CLI entry point."""
    stdin_data = sys.stdin.read().strip()

    if stdin_data:
        try:
            input_data = json.loads(stdin_data)
            if "__entrypoint__" in input_data:
                input_data = input_data["__input__"]
            text = input_data.get("text", "")
            source_lang = input_data.get("source_lang", "auto")
            target_lang = input_data.get("target_lang", "en")
        except json.JSONDecodeError:
            text = stdin_data
            source_lang = "auto"
            target_lang = "en"
    else:
        # CLI arguments
        import argparse
        parser = argparse.ArgumentParser(description="Translation tool")
        parser.add_argument("--text", type=str, help="Text to translate")
        parser.add_argument("--source", type=str, default="auto", help="Source language (zh/en/auto)")
        parser.add_argument("--target", type=str, default="en", help="Target language (zh/en)")
        args = parser.parse_args()
        text = args.text or ""
        source_lang = args.source
        target_lang = args.target

    if not text:
        print(json.dumps({"success": False, "error": "No text provided"}, ensure_ascii=False, indent=2))
        sys.exit(1)

    result = translate(text=text, source_lang=source_lang, target_lang=target_lang)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
