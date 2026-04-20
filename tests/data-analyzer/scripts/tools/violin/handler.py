#!/usr/bin/env python3
"""
Violin Plot Tool

Generates violin plot data and optional image files for visualizing numeric
variable distributions, especially when comparing across categorical groups.
"""
from typing import Any, Dict, List, Optional
import math
import json
from pathlib import Path

# Try to import matplotlib for image generation
MATPLOTLIB_AVAILABLE = False
try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    pass


def run(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run violin plot analysis.

    Args:
        params: Dictionary containing:
            - _data: List of data records (required, injected by framework)
            - _features: Data features detected by framework (optional)
            - variable: Numeric variable name (required)
            - group_by: Categorical variable for grouping (optional)
            - orientation: Plot orientation (optional)
            - include_boxplot: Whether to include boxplot data (optional)
            - output_format: Output format (optional)

    Returns:
        Dictionary with violin plot data
    """
    data = params.get("_data", [])
    features = params.get("_features", {})

    if not data:
        return {"error": "No data provided"}

    # Determine variable
    variable = params.get("variable", "auto")
    if variable == "auto":
        numeric_cols = features.get("numeric_cols", [])
        if not numeric_cols:
            numeric_cols = _detect_numeric_columns(data)
        variable = numeric_cols[0] if numeric_cols else None

    if not variable:
        return {"error": "No numeric variable specified"}

    # Determine group_by
    group_by = params.get("group_by", "auto")
    if group_by == "auto":
        suggested = features.get("suggested_grouping_vars", [])
        categorical_cols = features.get("categorical_cols", [])
        group_by = suggested[0] if suggested else (categorical_cols[0] if categorical_cols else None)

    orientation = params.get("orientation", "vertical")
    include_boxplot = params.get("include_boxplot", True)
    output_format = params.get("output_format", "json")

    # Extract data for the variable
    if group_by:
        # Grouped violin plot
        result = {
            "type": "violin_plot_grouped",
            "variable": variable,
            "group_by": group_by,
            "orientation": orientation,
            "groups": {}
        }

        # Get unique groups
        groups = {}
        for row in data:
            val = row.get(group_by)
            num_val = row.get(variable)

            if val is not None and num_val is not None:
                try:
                    num_val = float(num_val)
                    group_key = str(val)
                    if group_key not in groups:
                        groups[group_key] = []
                    groups[group_key].append(num_val)
                except (ValueError, TypeError):
                    pass

        for group_name, group_values in sorted(groups.items()):
            if len(group_values) >= 2:
                result["groups"][group_name] = _calculate_violin_data(
                    group_values, include_boxplot
                )

    else:
        # Single violin plot
        values = []
        for row in data:
            val = row.get(variable)
            if val is not None:
                try:
                    values.append(float(val))
                except (ValueError, TypeError):
                    pass

        if len(values) < 2:
            return {"error": "Not enough valid data points for violin plot"}

        result = {
            "type": "violin_plot",
            "variable": variable,
            "orientation": orientation,
            "data": _calculate_violin_data(values, include_boxplot)
        }

    # Add plotly spec if requested
    if output_format == "plotly":
        result["plotly_spec"] = _generate_plotly_spec(result)

    # Generate image file if matplotlib is available
    if MATPLOTLIB_AVAILABLE:
        image_path = _generate_violin_image(
            data, variable, group_by, orientation, include_boxplot
        )
        if image_path:
            result["image_path"] = image_path
    else:
        result["image_note"] = "matplotlib not available - only JSON data returned"

    return result


def _detect_numeric_columns(data: List[Dict]) -> List[str]:
    """Detect which columns contain numeric data."""
    if not data:
        return []

    numeric_cols = []
    first_row = data[0]

    for col in first_row.keys():
        is_numeric = True
        for row in data[:100]:
            val = row.get(col)
            if val is not None and val != "":
                if not isinstance(val, (int, float)):
                    try:
                        float(val)
                    except (ValueError, TypeError):
                        is_numeric = False
                        break
        if is_numeric:
            numeric_cols.append(col)

    return numeric_cols


def _calculate_violin_data(values: List[float], include_boxplot: bool) -> Dict[str, Any]:
    """
    Calculate violin plot data using kernel density estimation (KDE).

    Simplified KDE using gaussian kernels.
    """
    if not values:
        return {"error": "No data"}

    n = len(values)
    values_sorted = sorted(values)

    # Basic statistics
    min_val = values_sorted[0]
    max_val = values_sorted[-1]
    median_val = _percentile(values_sorted, 50)
    q1 = _percentile(values_sorted, 25)
    q3 = _percentile(values_sorted, 75)

    # Calculate KDE for violin shape
    kde_data = _calculate_kde(values_sorted)

    result = {
        "count": n,
        "min": min_val,
        "max": max_val,
        "median": median_val,
        "mean": round(sum(values) / n, 4),
        "q1": q1,
        "q3": q3,
        "iqr": q3 - q1,
        "kde": kde_data
    }

    if include_boxplot:
        result["boxplot"] = {
            "min": min_val,
            "q1": q1,
            "median": median_val,
            "q3": q3,
            "max": max_val,
            "whiskers": _calculate_whiskers(values_sorted, q1, q3)
        }

    return result


def _calculate_kde(values: List[float], n_points: int = 100) -> Dict[str, List]:
    """
    Calculate Kernel Density Estimation using gaussian kernels.

    Returns x and y coordinates for plotting the violin shape.
    """
    if len(values) < 2:
        return {"x": [], "y": []}

    # Use Silverman's rule for bandwidth
    n = len(values)
    std = math.sqrt(sum((x - sum(values) / n) ** 2 for x in values) / n)
    iqr = _percentile(values, 75) - _percentile(values, 25)
    bandwidth = 0.9 * min(std, iqr / 1.34) * (n ** -0.2)

    if bandwidth == 0:
        bandwidth = 1.0

    min_val = values[0]
    max_val = values[-1]
    range_val = max_val - min_val

    # Extend range slightly
    x_min = min_val - 0.1 * range_val
    x_max = max_val + 0.1 * range_val

    x = [x_min + (x_max - x_min) * i / (n_points - 1) for i in range(n_points)]
    y = [_kde_point(xi, values, bandwidth) for xi in x]

    # Normalize y to [0, 1] range for the violin shape
    max_y = max(y) if y else 1
    if max_y > 0:
        y = [yi / max_y for yi in y]

    return {"x": [round(v, 4) for v in x], "y": [round(v, 4) for v in y]}


def _kde_point(x: float, values: List[float], bandwidth: float) -> float:
    """Calculate KDE value at point x."""
    n = len(values)
    kernel_sum = sum(_gaussian_kernel((x - v) / bandwidth) for v in values)
    return kernel_sum / (n * bandwidth)


def _gaussian_kernel(u: float) -> float:
    """Standard gaussian kernel function."""
    return (1 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * u * u)


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


def _calculate_whiskers(values: List[float], q1: float, q3: float) -> Dict[str, float]:
    """Calculate whisker extents using Tukey's method."""
    iqr = q3 - q1
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr

    # Find actual whisker endpoints
    lower_whisker = min(v for v in values if v >= lower_fence)
    upper_whisker = max(v for v in values if v <= upper_fence)

    return {
        "lower": lower_whisker,
        "upper": upper_whisker,
        "lower_fence": lower_fence,
        "upper_fence": upper_fence
    }


def _generate_plotly_spec(result: Dict[str, Any]) -> Dict[str, Any]:
    """Generate Plotly figure specification for the violin plot."""
    spec = {
        "data": [],
        "layout": {
            "title": f"Violin Plot: {result.get('variable', 'Unknown')}",
            "xaxis": {"title": result.get("group_by", "")} if result.get("group_by") else {},
            "yaxis": {"title": result.get("variable", "")}
        }
    }

    # This is a simplified spec - full implementation would include traces
    if result.get("type") == "violin_plot_grouped":
        for group_name, group_data in result.get("groups", {}).items():
            kde = group_data.get("kde", {})
            spec["data"].append({
                "type": "scatter",
                "name": group_name,
                "x": kde.get("x", []),
                "y": kde.get("y", []),
                "mode": "lines",
                "fill": "tonexty"
            })

    return spec


def _generate_violin_image(
    data: List[Dict],
    variable: str,
    group_by: Optional[str],
    orientation: str,
    include_boxplot: bool
) -> Optional[str]:
    """
    Generate violin plot image and save to file.

    Returns:
        Path to saved image file, or None if generation failed.
    """
    try:
        # Create output directory
        output_dir = Path("/tmp/data_analyzer_plots")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Prepare data for plotting
        if group_by:
            # Grouped violin plot
            groups = {}
            for row in data:
                group_val = row.get(group_by)
                num_val = row.get(variable)
                if group_val is not None and num_val is not None:
                    try:
                        num_val = float(num_val)
                        group_key = str(group_val)
                        if group_key not in groups:
                            groups[group_key] = []
                        groups[group_key].append(num_val)
                    except (ValueError, TypeError):
                        pass

            if not groups:
                return None

            # Create grouped violin plot using matplotlib
            fig, ax = plt.subplots(figsize=(10, 6))

            # Prepare data for each group
            group_names = sorted(groups.keys())
            group_data = [groups[name] for name in group_names]

            # Create violin plot manually using box plot and individual points
            positions = range(1, len(group_names) + 1)
            parts = ax.violinplot(
                group_data,
                positions=positions,
                showmeans=True,
                showmedians=True,
                showextrema=True
            )

            # Style the violin plot
            for pc in parts['bodies']:
                pc.set_facecolor('#1f77b4')
                pc.set_alpha(0.7)

            ax.set_xticks(positions)
            ax.set_xticklabels(group_names)
            ax.set_xlabel(str(group_by))
            ax.set_ylabel(str(variable))
            ax.set_title(f'Violin Plot: {variable} by {group_by}')

            # Add grid
            ax.grid(True, alpha=0.3)
            ax.set_axisbelow(True)

        else:
            # Single violin plot
            values = []
            for row in data:
                val = row.get(variable)
                if val is not None:
                    try:
                        values.append(float(val))
                    except (ValueError, TypeError):
                        pass

            if len(values) < 2:
                return None

            fig, ax = plt.subplots(figsize=(8, 6))
            parts = ax.violinplot([values], showmeans=True, showmedians=True, showextrema=True)

            for pc in parts['bodies']:
                pc.set_facecolor('#1f77b4')
                pc.set_alpha(0.7)

            ax.set_xticks([1])
            ax.set_xticklabels([variable])
            ax.set_ylabel('Value')
            ax.set_title(f'Violin Plot: {variable}')
            ax.grid(True, alpha=0.3)
            ax.set_axisbelow(True)

        # Save figure
        filename = f"violin_{variable}"
        if group_by:
            filename += f"_by_{group_by}"
        filename += ".png"

        output_path = output_dir / filename
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close(fig)

        return str(output_path)

    except Exception as e:
        # Return error info rather than failing completely
        return None
