#!/usr/bin/env python3
"""
Data Analyzer - Main Entry Point

This script provides intelligent data analysis capabilities with automatic
tool discovery and parameter configuration.

Usage:
    # Scan data and get features
    python analyze.py --scan data.csv

    # List all available tools
    python analyze.py --list-tools

    # Run a specific analysis
    python analyze.py --run descriptives --data data.csv

    # Let AI decide and run
    python analyze.py --auto-analyze data.csv
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from common.data_loader import load_data
from common.type_detector import detect_data_features
from common.utils import load_json, save_json, format_output


# Directory structure
SCRIPT_DIR = Path(__file__).parent
TOOLS_DIR = SCRIPT_DIR / "tools"
REGISTRY_FILE = SCRIPT_DIR / "registry.json"


def list_tools() -> Dict[str, Any]:
    """
    List all available analysis tools.

    Returns:
        Dictionary with tool information indexed by tool name.
    """
    tools = {}

    if not TOOLS_DIR.exists():
        return {"error": "Tools directory not found"}

    for tool_dir in TOOLS_DIR.iterdir():
        if not tool_dir.is_dir():
            continue

        meta_file = tool_dir / "meta.json"
        if not meta_file.exists():
            continue

        meta = load_json(str(meta_file))
        if meta:
            tool_name = meta.get("name", tool_dir.name)
            tools[tool_name] = {
                "path": str(tool_dir),
                "name": tool_name,
                "description": meta.get("description", ""),
                "when_to_use": meta.get("when_to_use", []),
                "parameters": meta.get("parameters", {}),
                "data_requirements": meta.get("data_requirements", {}),
                "output": meta.get("output", {})
            }

    return tools


def scan_data(data_path: str) -> Dict[str, Any]:
    """
    Scan data file and extract features for intelligent tool selection.

    Returns:
        Dictionary with data features and suggested tools.
    """
    # Load data
    loaded = load_data(data_path)
    if "error" in loaded:
        return loaded

    # Detect features
    features = detect_data_features(loaded)
    if "error" in features:
        return features

    # Get available tools
    tools = list_tools()

    # Match tools to data
    matched_tools = []
    for tool_name, tool_info in tools.items():
        if _check_tool_requirements(features, tool_info.get("data_requirements", {})):
            matched_tools.append({
                "name": tool_name,
                "description": tool_info.get("description", ""),
                "why": _explain_tool_match(features, tool_info)
            })

    return {
        "data_file": data_path,
        "data_info": {
            "rows": loaded.get("rows"),
            "columns": loaded.get("columns"),
            "format": loaded.get("format")
        },
        "features": features,
        "available_tools": list(tools.keys()),
        "matched_tools": matched_tools,
        "suggested_analysis": features.get("suggested_analysis", [])
    }


def _check_tool_requirements(features: Dict[str, Any], requirements: Dict[str, Any]) -> bool:
    """Check if data meets tool requirements."""
    # Check minimum columns
    min_cols = requirements.get("min_columns", 0)
    n_cols = len(features.get("numeric_cols", [])) + len(features.get("categorical_cols", []))
    if n_cols < min_cols:
        return False

    # Check column types
    required_types = requirements.get("column_types", [])
    if required_types:
        for req_type in required_types:
            if req_type == "numeric" and not features.get("numeric_cols"):
                return False
            if req_type == "categorical" and not features.get("categorical_cols"):
                return False

    # Check minimum rows
    min_rows = requirements.get("min_rows", 0)
    # This would need actual row count from data
    # For now, assume data has enough rows if it loaded successfully

    return True


def _explain_tool_match(features: Dict[str, Any], tool_info: Dict[str, Any]) -> str:
    """Generate explanation for why a tool matches the data."""
    reasons = []

    numeric = features.get("numeric_cols", [])
    categorical = features.get("categorical_cols", [])

    if numeric and "numeric" in tool_info.get("data_requirements", {}).get("column_types", []):
        reasons.append(f"has {len(numeric)} numeric column(s)")

    if categorical and "categorical" in tool_info.get("data_requirements", {}).get("column_types", []):
        reasons.append(f"has {len(categorical)} categorical column(s)")

    return " and ".join(reasons) if reasons else "matches data characteristics"


def run_tool(tool_name: str, data_path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Run a specific analysis tool.

    Args:
        tool_name: Name of the tool to run
        data_path: Path to data file
        params: Optional parameters (will use defaults if not provided)

    Returns:
        Tool execution results
    """
    # Get tool info
    tools = list_tools()
    if tool_name not in tools:
        return {"error": f"Tool '{tool_name}' not found. Available: {list(tools.keys())}"}

    tool_info = tools[tool_name]
    tool_path = Path(tool_info["path"])

    # Load defaults
    defaults_file = tool_path / "defaults.json"
    defaults = load_json(str(defaults_file)) if defaults_file.exists() else {}

    # Merge parameters
    final_params = defaults.copy()
    if params:
        final_params.update(params)

    # Import and run handler
    handler_file = tool_path / "handler.py"
    if not handler_file.exists():
        return {"error": f"Handler not found for tool '{tool_name}'"}

    # Load data
    loaded = load_data(data_path)
    if "error" in loaded:
        return {"error": f"Data loading failed: {loaded['error']}"}

    # Get features for intelligent defaults
    features = detect_data_features(loaded)

    # Add data and features to params
    final_params["_data"] = loaded.get("data", [])
    final_params["_features"] = features

    # Import handler dynamically
    try:
        # Add tool directory to path
        sys.path.insert(0, str(tool_path))

        # Import handler module
        import importlib.util
        spec = importlib.util.spec_from_file_location("handler", handler_file)
        handler_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(handler_module)

        # Call run function
        if hasattr(handler_module, "run"):
            result = handler_module.run(final_params)
        else:
            result = {"error": "Handler must have a 'run' function"}

        return {
            "tool": tool_name,
            "data_file": data_path,
            "params": {k: v for k, v in final_params.items() if not k.startswith("_")},
            "result": result
        }

    except Exception as e:
        return {"error": f"Tool execution failed: {e}"}


def auto_analyze(data_path: str, tools: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Automatically analyze data using AI-selected tools.

    Args:
        data_path: Path to data file
        tools: Optional list of specific tools to run (auto-select if None)

    Returns:
        Combined analysis results
    """
    # Scan data first
    scan_result = scan_data(data_path)
    if "error" in scan_result:
        return scan_result

    # Determine which tools to run
    if tools is None:
        # Use suggested tools from scan
        tool_names = scan_result.get("suggested_analysis", [])
    else:
        tool_names = tools

    if not tool_names:
        return {
            **scan_result,
            "warning": "No tools selected for analysis",
            "results": []
        }

    # Run each tool
    results = []
    for tool_name in tool_names:
        result = run_tool(tool_name, data_path)
        results.append(result)

    return {
        "data_file": data_path,
        "data_summary": scan_result.get("data_info"),
        "tools_executed": tool_names,
        "results": results
    }


def generate_registry() -> bool:
    """Generate registry.json file from available tools."""
    tools = list_tools()
    return save_json({"tools": list(tools.keys()), "tools_info": tools}, str(REGISTRY_FILE))


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Data Analyzer - Intelligent data analysis with automatic tool selection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan data and see what tools can be used
  python analyze.py --scan data.csv

  # List all available analysis tools
  python analyze.py --list-tools

  # Run a specific tool
  python analyze.py --run descriptives --data data.csv

  # Run with custom parameters
  python analyze.py --run descriptives --data data.csv --params '{"variables": ["age", "score"]}'

  # Let AI automatically decide and run analysis
  python analyze.py --auto-analyze data.csv

  # Generate/update registry file
  python analyze.py --generate-registry
        """
    )

    parser.add_argument("--scan", metavar="FILE", help="Scan data file and show features")
    parser.add_argument("--list-tools", action="store_true", help="List all available tools")
    parser.add_argument("--run", metavar="TOOL", help="Run a specific tool")
    parser.add_argument("--data", metavar="FILE", help="Data file path (use with --run)")
    parser.add_argument("--params", metavar="JSON", help="Parameters as JSON string")
    parser.add_argument("--auto-analyze", metavar="FILE", help="Automatically analyze data")
    parser.add_argument("--tools", metavar="TOOLS", help="Comma-separated list of tools for auto-analyze")
    parser.add_argument("--generate-registry", action="store_true", help="Generate registry.json")
    parser.add_argument("--output", choices=["json", "compact"], default="json", help="Output format")

    args = parser.parse_args()

    result = None

    if args.generate_registry:
        success = generate_registry()
        result = {"status": "success" if success else "failed"}

    elif args.list_tools:
        result = {"tools": list_tools()}

    elif args.scan:
        result = scan_data(args.scan)

    elif args.run:
        if not args.data:
            parser.error("--data is required when using --run")
        params = json.loads(args.params) if args.params else None
        result = run_tool(args.run, args.data, params)

    elif args.auto_analyze:
        tools = args.tools.split(",") if args.tools else None
        result = auto_analyze(args.auto_analyze, tools)

    else:
        parser.print_help()
        sys.exit(1)

    # Output result
    if args.output == "compact":
        print(json.dumps(result, ensure_ascii=False, separators=(',', ':')))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


def _get_data_path(params: Dict[str, Any]) -> Optional[str]:
    """Get data path from params, supporting both 'data' and 'file_path' keys."""
    return params.get("data") or params.get("file_path")


if __name__ == "__main__":
    # Handle JSON input via stdin for skill execution
    if len(sys.argv) == 1 and not sys.stdin.isatty():
        stdin_data = sys.stdin.read().strip()
        if stdin_data:
            try:
                input_data = json.loads(stdin_data)
                # UniversalScriptExecutor format
                if "__entrypoint__" in input_data:
                    input_params = input_data.get("__input__", {})

                    # Dispatch based on action (default: scan)
                    action = input_params.get("action", "scan")

                    if action == "scan":
                        data_path = _get_data_path(input_params)
                        result = scan_data(data_path) if data_path else {"error": "No data file path provided"}
                    elif action == "list_tools":
                        result = {"tools": list_tools()}
                    elif action == "run":
                        data_path = _get_data_path(input_params)
                        if not data_path:
                            result = {"error": "No data file path provided"}
                        else:
                            result = run_tool(
                                input_params.get("tool"),
                                data_path,
                                input_params.get("params")
                            )
                    elif action == "auto_analyze":
                        data_path = _get_data_path(input_params)
                        result = auto_analyze(data_path, input_params.get("tools")) if data_path else {"error": "No data file path provided"}
                    else:
                        result = {"error": f"Unknown action: {action}"}
                else:
                    result = {"error": "Invalid input format"}
            except json.JSONDecodeError:
                result = {"error": "Invalid JSON input"}
        else:
            result = {"error": "No input provided"}

        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        main()
