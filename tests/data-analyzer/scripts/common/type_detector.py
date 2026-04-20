#!/usr/bin/env python3
"""
Automatic data type detection for intelligent tool selection.
"""
from typing import Any, Dict, List, Optional, Set
import re


def detect_data_features(loaded_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze loaded data and extract features for tool selection.

    Returns:
        Dictionary with data features including:
        - numeric_cols: List of numeric column names
        - categorical_cols: List of categorical column names
        - binary_cols: List of binary columns
        - datetime_cols: List of datetime columns
        - text_cols: List of text columns
        - column_details: Detailed info for each column
    """
    if "error" in loaded_data:
        return {"error": loaded_data["error"]}

    data = loaded_data.get("data", [])
    if not data:
        return {"error": "No data to analyze"}

    columns = loaded_data.get("columns", [])
    if not columns:
        return {"error": "No columns found"}

    features = {
        "numeric_cols": [],
        "categorical_cols": [],
        "binary_cols": [],
        "datetime_cols": [],
        "text_cols": [],
        "column_details": {},
        "suggested_grouping_vars": [],
        "suggested_analysis": []
    }

    for col in columns:
        col_info = _analyze_column(data, col)
        features["column_details"][col] = col_info

        if col_info["type"] == "numeric":
            features["numeric_cols"].append(col)
        elif col_info["type"] == "categorical":
            features["categorical_cols"].append(col)
            if col_info["n_unique"] <= 10:
                features["suggested_grouping_vars"].append(col)
        elif col_info["type"] == "binary":
            features["binary_cols"].append(col)
            if col_info["n_unique"] <= 2:
                features["suggested_grouping_vars"].append(col)
        elif col_info["type"] == "datetime":
            features["datetime_cols"].append(col)
        elif col_info["type"] == "text":
            features["text_cols"].append(col)

    # Generate analysis suggestions
    features["suggested_analysis"] = _generate_suggestions(features)

    return features


def _analyze_column(data: List[Dict[str, Any]], column: str) -> Dict[str, Any]:
    """Analyze a single column and determine its characteristics."""
    values = [row.get(column) for row in data if column in row and row.get(column) is not None and row.get(column) != ""]

    if not values:
        return {
            "type": "empty",
            "n_valid": 0,
            "n_missing": len(data),
            "n_unique": 0,
            "missing_rate": 1.0
        }

    n_valid = len(values)
    n_missing = len(data) - n_valid
    unique_values = set(values)
    n_unique = len(unique_values)

    # Try to detect type
    detected_type, metadata = _detect_column_type(values, unique_values)

    return {
        "type": detected_type,
        "n_valid": n_valid,
        "n_missing": n_missing,
        "n_unique": n_unique,
        "missing_rate": n_missing / len(data),
        "unique_values": list(unique_values)[:20],  # Limit to 20
        **metadata
    }


def _detect_column_type(values: List[Any], unique_values: Set[Any]) -> tuple:
    """Detect the most likely type of a column."""
    numeric_count = 0
    datetime_count = 0
    text_count = 0

    for v in values[:100]:  # Sample first 100 values
        if isinstance(v, (int, float)):
            numeric_count += 1
        elif isinstance(v, str):
            # Check if it's a number string
            if _is_numeric_string(v):
                numeric_count += 1
            elif _is_datetime_string(v):
                datetime_count += 1
            else:
                text_count += 1

    total = min(len(values), 100)

    # Determine type based on majority
    if numeric_count / total > 0.8:
        return "numeric", _get_numeric_metadata(values)
    elif datetime_count / total > 0.5:
        return "datetime", {}
    elif text_count / total > 0.5:
        if len(unique_values) <= 10:
            return "categorical", {"categories": list(unique_values)}
        elif len(unique_values) == 2:
            return "binary", {"categories": list(unique_values)}
        else:
            return "text", {"avg_length": sum(len(str(v)) for v in values) / len(values)}
    else:
        # Mixed or uncertain - check unique count
        if len(unique_values) <= 10:
            return "categorical", {"categories": list(unique_values)}
        return "text", {}


def _is_numeric_string(s: str) -> bool:
    """Check if string represents a number."""
    try:
        float(s)
        return True
    except ValueError:
        return False


def _is_datetime_string(s: str) -> bool:
    """Check if string looks like a datetime."""
    datetime_patterns = [
        r'\d{4}-\d{2}-\d{2}',           # 2024-01-01
        r'\d{4}/\d{2}/\d{2}',           # 2024/01/01
        r'\d{2}-\d{2}-\d{4}',           # 01-01-2024
        r'\d{2}/\d{2}/\d{4}',           # 01/01/2024
    ]
    return any(re.search(p, s) for p in datetime_patterns)


def _get_numeric_metadata(values: List[Any]) -> Dict[str, Any]:
    """Get metadata for numeric columns."""
    numeric_values = []
    for v in values:
        if isinstance(v, (int, float)):
            numeric_values.append(v)
        elif isinstance(v, str) and _is_numeric_string(v):
            numeric_values.append(float(v))

    if not numeric_values:
        return {}

    return {
        "min": min(numeric_values),
        "max": max(numeric_values),
        "mean": sum(numeric_values) / len(numeric_values),
        "sample_values": numeric_values[:5]
    }


def _generate_suggestions(features: Dict[str, Any]) -> List[str]:
    """Generate analysis suggestions based on data features."""
    suggestions = []

    numeric = features.get("numeric_cols", [])
    categorical = features.get("suggested_grouping_vars", [])

    if numeric:
        if len(numeric) == 1:
            suggestions.append("descriptives")
        else:
            suggestions.extend(["descriptives", "correlation"])

    if len(numeric) >= 1 and categorical:
        suggestions.extend(["violin", "boxplot"])

    if len(categorical) >= 2:
        suggestions.append("crosstab")

    if features.get("datetime_cols"):
        suggestions.append("time_series")

    return list(set(suggestions))  # Remove duplicates
