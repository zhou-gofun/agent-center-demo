#!/usr/bin/env python3
"""
Common utility functions for data analysis tools.
"""
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_json(file_path: str) -> Dict[str, Any]:
    """Load JSON file with error handling."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing {file_path}: {e}", file=sys.stderr)
        return {}


def save_json(data: Dict[str, Any], file_path: str, indent: int = 2) -> bool:
    """Save data to JSON file."""
    try:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        return True
    except Exception as e:
        print(f"Error saving {file_path}: {e}", file=sys.stderr)
        return False


def merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge two config dictionaries."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    return result


def validate_parameters(params: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """Validate parameters against schema. Returns list of errors."""
    errors = []

    for param_name, param_config in schema.get("parameters", {}).items():
        # Check required parameters
        if param_config.get("required", False) and param_name not in params:
            errors.append(f"Required parameter '{param_name}' is missing")

        # Check type if provided
        if param_name in params and "type" in param_config:
            expected_type = param_config["type"]
            actual_value = params[param_name]

            if expected_type == "array" and not isinstance(actual_value, list):
                errors.append(f"Parameter '{param_name}' should be an array")
            elif expected_type == "string" and not isinstance(actual_value, str):
                errors.append(f"Parameter '{param_name}' should be a string")
            elif expected_type == "number" and not isinstance(actual_value, (int, float)):
                errors.append(f"Parameter '{param_name}' should be a number")
            elif expected_type == "boolean" and not isinstance(actual_value, bool):
                errors.append(f"Parameter '{param_name}' should be a boolean")

    return errors


def format_output(result: Any, output_type: str = "json") -> str:
    """Format output according to specified type."""
    if output_type == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif output_type == "compact":
        return json.dumps(result, ensure_ascii=False, separators=(',', ':'))
    else:
        return str(result)
