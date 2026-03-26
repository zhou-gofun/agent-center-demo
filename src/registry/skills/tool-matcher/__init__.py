"""
Tool Matcher Skill - Python实现

根据分析需求匹配最合适的统计工具
"""
from typing import Dict, Any
import sys
from pathlib import Path

# Add scripts directory to path for import
scripts_dir = Path(__file__).parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from match import match_tools as _match


def execute(input_data: Dict) -> Dict[str, Any]:
    """
    执行工具匹配

    Args:
        input_data: 包含 query, top_k, use_vector 等信息

    Returns:
        匹配结果字典
    """
    query = input_data.get("query", "")
    top_k = input_data.get("top_k", 10)
    use_vector = input_data.get("use_vector", False)

    return _match(query, top_k, use_vector)
