#!/usr/bin/env python3
"""
Descriptive Statistics Tool

Calculates descriptive statistics for numeric variables including
mean, standard deviation, median, quartiles, min, max, etc.
"""
from typing import Any, Dict, List, Optional
import math


def run(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run descriptive statistics analysis.

    Args:
        params: Dictionary containing:
            - _data: List of data records (required, injected by framework)
            - _features: Data features detected by framework (optional)
            - variables: List of variable names or "all_numeric" (optional)
            - group_by: Column name for grouping (optional)
            - percentiles: List of percentiles to calculate (optional)
            - include: List of statistics to include (optional)

    Returns:
        Dictionary with descriptive statistics results
    """
    data = params.get("_data", [])
    features = params.get("_features", {})

    if not data:
        return {"error": "No data provided"}

    # Determine which variables to analyze
    variables = params.get("variables", "all_numeric")
    if variables == "all_numeric":
        numeric_cols = features.get("numeric_cols", [])
        if not numeric_cols:
            # Fallback: detect numeric columns
            numeric_cols = _detect_numeric_columns(data)
        variables = numeric_cols

    if not variables:
        return {"error": "No numeric variables found"}

    # Get other parameters
    group_by = params.get("group_by")
    percentiles = params.get("percentiles", [25, 50, 75, 90, 95, 99])
    include = params.get("include", ["count", "mean", "std", "min", "max", "median", "q1", "q3"])

    # Calculate statistics
    if group_by and group_by in str(data[0].keys()):
        # Grouped statistics
        result = {
            "type": "grouped_descriptives",
            "group_by": group_by,
            "variables": variables,
            "groups": {}
        }

        # Get unique groups
        groups = set()
        for row in data:
            val = row.get(group_by)
            if val is not None:
                groups.add(val)

        for group in sorted(groups):
            group_data = [row for row in data if row.get(group_by) == group]
            result["groups"][str(group)] = _calculate_stats_for_variables(
                group_data, variables, percentiles, include
            )
    else:
        # Overall statistics
        result = {
            "type": "descriptives",
            "variables": variables,
            "statistics": _calculate_stats_for_variables(
                data, variables, percentiles, include
            )
        }

    return result


def _detect_numeric_columns(data: List[Dict]) -> List[str]:
    """Detect which columns contain numeric data."""
    if not data:
        return []

    numeric_cols = []
    first_row = data[0]

    for col in first_row.keys():
        is_numeric = True
        for row in data[:100]:  # Check first 100 rows
            val = row.get(col)
            if val is not None and val != "":
                if not isinstance(val, (int, float)):
                    # Try to convert to number
                    try:
                        float(val)
                    except (ValueError, TypeError):
                        is_numeric = False
                        break
        if is_numeric:
            numeric_cols.append(col)

    return numeric_cols


def _calculate_stats_for_variables(
    data: List[Dict],
    variables: List[str],
    percentiles: List[int],
    include: List[str]
) -> Dict[str, Dict[str, Any]]:
    """Calculate statistics for specified variables."""
    result = {}

    for var in variables:
        # Extract values for this variable
        values = []
        for row in data:
            val = row.get(var)
            if val is not None and val != "":
                try:
                    values.append(float(val))
                except (ValueError, TypeError):
                    pass

        if not values:
            result[var] = {"error": "No valid numeric values"}
            continue

        # Calculate statistics
        stats = {}
        values_sorted = sorted(values)
        n = len(values)

        if "count" in include:
            stats["count"] = n

        if "mean" in include:
            stats["mean"] = round(sum(values) / n, 4)

        if "std" in include:
            mean = sum(values) / n
            variance = sum((x - mean) ** 2 for x in values) / n
            stats["std"] = round(math.sqrt(variance), 4)

        if "var" in include:
            mean = sum(values) / n
            variance = sum((x - mean) ** 2 for x in values) / n
            stats["var"] = round(variance, 4)

        if "min" in include:
            stats["min"] = values_sorted[0]

        if "max" in include:
            stats["max"] = values_sorted[-1]

        if "median" in include:
            stats["median"] = _percentile(values_sorted, 50)

        if "q1" in include:
            stats["q1"] = _percentile(values_sorted, 25)

        if "q3" in include:
            stats["q3"] = _percentile(values_sorted, 75)

        if "percentiles" in include:
            stats["percentiles"] = {
                f"p{p}": _percentile(values_sorted, p) for p in percentiles
            }

        if "sum" in include:
            stats["sum"] = round(sum(values), 4)

        if "skew" in include:
            stats["skew"] = _calculate_skew(values)

        if "kurtosis" in include:
            stats["kurtosis"] = _calculate_kurtosis(values)

        result[var] = stats

    return result


def _percentile(sorted_values: List[float], p: int) -> float:
    """Calculate percentile using linear interpolation."""
    n = len(sorted_values)
    if n == 0:
        return 0

    index = (p / 100) * (n - 1)
    lower = int(index)
    upper = lower + 1

    if upper >= n:
        return sorted_values[-1]

    weight = index - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def _calculate_skew(values: List[float]) -> float:
    """Calculate skewness (third standardized moment)."""
    n = len(values)
    if n < 3:
        return 0

    mean = sum(values) / n
    std = math.sqrt(sum((x - mean) ** 2 for x in values) / n)

    if std == 0:
        return 0

    skew = sum((x - mean) ** 3 for x in values) / (n * std ** 3)
    return round(skew, 4)


def _calculate_kurtosis(values: List[float]) -> float:
    """Calculate kurtosis (fourth standardized moment)."""
    n = len(values)
    if n < 4:
        return 0

    mean = sum(values) / n
    std = math.sqrt(sum((x - mean) ** 2 for x in values) / n)

    if std == 0:
        return 0

    kurt = sum((x - mean) ** 4 for x in values) / (n * std ** 4) - 3
    return round(kurt, 4)
