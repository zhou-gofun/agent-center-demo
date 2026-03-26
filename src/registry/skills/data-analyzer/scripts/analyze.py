#!/usr/bin/env python3
"""
Data Analyzer Script

Analyzes data summaries and extracts key features.
"""
import argparse
import json
import re
import sys
from typing import Dict, List, Any, Optional


def analyze_data(data_summary: str) -> Dict[str, Any]:
    """
    Analyze data summary and extract features.

    Args:
        data_summary: Data summary text (skimr format or structured description)

    Returns:
        Dictionary with extracted features
    """
    if not data_summary or not isinstance(data_summary, str):
        return {
            "sample_size": None,
            "n_variables": None,
            "variable_types": {"numeric": [], "categorical": [], "binary": [], "ordinal": []},
            "grouping_variables": [],
            "study_design": "unknown",
            "missing_data": {},
            "statistical_characteristics": {},
            "raw_variables": [],
        }

    summary_lower = data_summary.lower()

    return {
        "sample_size": extract_sample_size(data_summary),
        "n_variables": extract_n_variables(data_summary),
        "variable_types": extract_variable_types(data_summary),
        "grouping_variables": identify_grouping_variables(data_summary),
        "study_design": identify_study_design(summary_lower),
        "missing_data": detect_missing_data(data_summary),
        "statistical_characteristics": extract_statistics(data_summary),
        "raw_variables": extract_raw_variables(data_summary),
    }


def extract_sample_size(summary: str) -> Optional[int]:
    """Extract sample size from summary."""
    patterns = [
        r"n\s*obs\s*:?\s*(\d+)",
        r"n\s*[:=]\s*(\d+)",
        r"sample\s*size\s*:?\s*(\d+)",
        r"total\s*[ns]?\s*:?\s*(\d+)",
        r"\bn\s*=\s*(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, summary, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                continue
    return None


def extract_n_variables(summary: str) -> Optional[int]:
    """Extract number of variables from summary."""
    patterns = [
        r"n\s*variables\s*:?\s*(\d+)",
        r"variables?\s*:?\s*(\d+)",
        r"number\s+of\s+variables?\s*:?\s*(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, summary, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                continue
    return None


def extract_variable_types(summary: str) -> Dict[str, List[str]]:
    """Extract variable types from summary."""
    types = {"numeric": [], "categorical": [], "binary": [], "ordinal": []}

    lines = summary.split('\n')
    for line in lines:
        if not line.strip() or line.strip().startswith('#'):
            continue

        parts = line.strip().split()
        if len(parts) >= 2:
            potential_var = parts[0]
            if re.match(r'^[a-z_][a-z0-9_]*$', potential_var, re.IGNORECASE):
                context_lower = summary.lower()
                if any(x in context_lower for x in ["numeric", "continuous"]):
                    types["numeric"].append(potential_var)
                elif any(x in context_lower for x in ["categorical", "factor"]):
                    types["categorical"].append(potential_var)

    return types


def extract_raw_variables(summary: str) -> List[str]:
    """Extract all variable names from summary."""
    variables = []
    lines = summary.split('\n')

    for line in lines:
        if not line.strip() or line.strip().startswith('#'):
            continue

        parts = line.strip().split()
        if len(parts) >= 2:
            potential_var = parts[0]
            if re.match(r'^[a-z_][a-z0-9_]*$', potential_var, re.IGNORECASE):
                if potential_var not in variables:
                    variables.append(potential_var)

    return variables


def identify_study_design(summary_lower: str) -> str:
    """Identify study design from summary."""
    study_designs = {
        "randomized_controlled_trial": ["rct", "randomized", "randomised", "controlled trial"],
        "cohort_study": ["cohort", "longitudinal", "follow-up", "prospective"],
        "case_control": ["case control", "case-control", "case-control study"],
        "cross_sectional": ["cross sectional", "cross-sectional", "survey"],
        "case_series": ["case series", "case report"],
        "meta_analysis": ["meta-analysis", "meta analysis", "systematic review"]
    }

    for design, patterns in study_designs.items():
        for pattern in patterns:
            if pattern in summary_lower:
                return design
    return "unknown"


def identify_grouping_variables(summary: str) -> List[str]:
    """Identify potential grouping variables."""
    grouping_vars = []
    grouping_patterns = [
        r"\bgroup\b", r"\btreatment\b", r"\bcondition\b",
        r"\barm\b", r"\bcohort\b", r"\bcategory\b", r"\bclass\b"
    ]

    lines = summary.split('\n')
    for line in lines:
        words = re.findall(r'\b[a-z_][a-z0-9_]*\b', line, re.IGNORECASE)
        for word in words:
            word_lower = word.lower()
            for pattern in grouping_patterns:
                if re.search(pattern, word_lower):
                    if word not in grouping_vars:
                        grouping_vars.append(word)

    return grouping_vars


def extract_statistics(summary: str) -> Dict[str, Any]:
    """Extract statistical characteristics."""
    stats = {}
    patterns = {
        "mean": r"mean\s*[:=]\s*([-\d.]+)",
        "sd": r"\bsd\s*[:=]\s*([-\d.]+)",
        "min": r"\bmin\s*[:=]\s*([-\d.]+)",
        "max": r"\bmax\s*[:=]\s*([-\d.]+)",
        "median": r"median\s*[:=]\s*([-\d.]+)",
        "p_value": r"\bp\s*[:=]\s*([-\d.]+)",
    }

    for stat_name, pattern in patterns.items():
        matches = re.findall(pattern, summary, re.IGNORECASE)
        if matches:
            try:
                stats[stat_name] = [float(m) for m in matches[:5]]
            except ValueError:
                pass

    return stats


def detect_missing_data(summary: str) -> Dict[str, Any]:
    """Detect missing data patterns."""
    missing = {}
    patterns = [
        r"missing\s*:?\s*(\d+)",
        r"na\s*:?\s*(\d+)",
        r"complete\s*cases?\s*:?\s*(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, summary, re.IGNORECASE)
        if match:
            missing["detected"] = True
            try:
                missing["count"] = int(match.group(1))
            except (ValueError, IndexError):
                pass
            break

    return missing


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Analyze data summaries")
    parser.add_argument("--data-summary", type=str, help="Data summary text")
    parser.add_argument("--file", type=str, help="File containing data summary")

    args = parser.parse_args()

    if args.file:
        with open(args.file, 'r') as f:
            data_summary = f.read()
    elif args.data_summary:
        data_summary = args.data_summary
    else:
        # Read from stdin
        data_summary = sys.stdin.read()

    result = analyze_data(data_summary)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
