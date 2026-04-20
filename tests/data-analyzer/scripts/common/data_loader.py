#!/usr/bin/env python3
"""
Data loading utilities supporting multiple formats.
"""
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def load_data(data_path: str) -> Dict[str, Any]:
    """
    Load data from various formats.

    Supports:
    - CSV files (.csv)
    - JSON files (.json)
    - JSON Lines files (.jsonl)

    Returns:
        Dictionary with:
        - data: List of records (dicts)
        - format: Detected format
        - path: Original file path
        - rows: Number of rows
        - columns: List of column names
    """
    path = Path(data_path)

    if not path.exists():
        return {"error": f"File not found: {data_path}"}

    suffix = path.suffix.lower()

    if suffix == '.csv':
        return _load_csv(data_path)
    elif suffix == '.json':
        return _load_json(data_path)
    elif suffix == '.jsonl':
        return _load_jsonl(data_path)
    else:
        return {"error": f"Unsupported file format: {suffix}"}


def _load_csv(file_path: str) -> Dict[str, Any]:
    """Load CSV file."""
    try:
        data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(dict(row))

        if data:
            return {
                "data": data,
                "format": "csv",
                "path": file_path,
                "rows": len(data),
                "columns": list(data[0].keys())
            }
        else:
            return {"error": "CSV file is empty"}
    except Exception as e:
        return {"error": f"Error loading CSV: {e}"}


def _load_json(file_path: str) -> Dict[str, Any]:
    """Load JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        # Handle different JSON structures
        if isinstance(json_data, list):
            data = json_data
        elif isinstance(json_data, dict):
            if "data" in json_data:
                data = json_data["data"]
            elif "records" in json_data:
                data = json_data["records"]
            else:
                # Try to use dict values as data
                data = [json_data]
        else:
            return {"error": "Unsupported JSON structure"}

        if not isinstance(data, list):
            return {"error": "JSON data must be a list or object with data/records"}

        if data and isinstance(data[0], dict):
            return {
                "data": data,
                "format": "json",
                "path": file_path,
                "rows": len(data),
                "columns": list(data[0].keys())
            }
        else:
            return {"error": "JSON data must contain objects with key-value pairs"}

    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {e}"}
    except Exception as e:
        return {"error": f"Error loading JSON: {e}"}


def _load_jsonl(file_path: str) -> Dict[str, Any]:
    """Load JSON Lines file."""
    try:
        data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    data.append(json.loads(line))

        if data:
            return {
                "data": data,
                "format": "jsonl",
                "path": file_path,
                "rows": len(data),
                "columns": list(data[0].keys())
            }
        else:
            return {"error": "JSONL file is empty"}
    except Exception as e:
        return {"error": f"Error loading JSONL: {e}"}


def get_column_values(data: List[Dict[str, Any]], column: str) -> List[Any]:
    """Extract values for a specific column."""
    return [row.get(column) for row in data if column in row]


def filter_data(data: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Filter data based on column values."""
    result = data
    for column, value in filters.items():
        result = [row for row in result if row.get(column) == value]
    return result
