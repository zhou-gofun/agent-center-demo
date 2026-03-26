"""
Semantic Search Skill - Python实现

在知识库中进行向量语义搜索
"""
from typing import Dict, Any
import sys
from pathlib import Path

# Add scripts directory to path for import
scripts_dir = Path(__file__).parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from search import semantic_search as _search


def execute(input_data: Dict) -> Dict[str, Any]:
    """
    执行语义搜索

    Args:
        input_data: 包含 query, collection, top_k 等信息

    Returns:
        搜索结果字典
    """
    query = input_data.get("query", "")
    collection = input_data.get("collection", "assembly_tools")
    top_k = input_data.get("top_k", 10)

    return _search(query, collection, top_k)
