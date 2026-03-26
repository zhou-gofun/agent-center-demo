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

    result = _search(query, collection, top_k)

    # 如果向量数据库不可用，返回关键词匹配回退
    if result.get("error") and "Collection" in result.get("error", ""):
        # 回退到基于关键词的工具推荐
        return _fallback_keyword_match(query, top_k)

    return result


def _fallback_keyword_match(query: str, top_k: int = 10) -> Dict[str, Any]:
    """
    回退方案：基于关键词匹配推荐工具

    当向量数据库不可用时使用
    """
    import re

    # 生存分析相关工具推荐
    survival_tools = [
        {
            "toolid": "cox_regression",
            "toolname": "Cox Proportional Hazards Regression",
            "idname": "cox_ph",
            "description": "Cox比例风险回归模型，用于生存分析，评估多个协变量对生存时间的影响",
            "keywords": ["cox", "regression", "survival", "hazard", "proportional", "风险"],
            "applications": "生存分析、多因素风险评估"
        },
        {
            "toolid": "kaplan_meier",
            "toolname": "Kaplan-Meier Survival Curve",
            "idname": "km_curve",
            "description": "Kaplan-Meier生存曲线，用于估计生存函数并可视化不同组的生存情况",
            "keywords": ["kaplan", "meier", "km", "survival", "curve", "生存曲线"],
            "applications": "生存曲线绘制、组间生存比较"
        },
        {
            "toolid": "logrank_test",
            "toolname": "Log-Rank Test",
            "idname": "logrank",
            "description": "Log-rank检验，用于比较两组或多组生存曲线是否有差异",
            "keywords": ["logrank", "log-rank", "test", "survival", "compare", "生存检验"],
            "applications": "组间生存曲线比较"
        },
        {
            "toolid": "survival_summary",
            "toolname": "Survival Data Summary",
            "idname": "survival_summary",
            "description": "生存数据汇总统计，包括中位生存时间、生存率等",
            "keywords": ["summary", "descriptive", "median", "survival", "time"],
            "applications": "生存数据描述性统计"
        }
    ]

    # 根据查询关键词匹配
    query_lower = query.lower()
    matched = []

    for tool in survival_tools:
        score = 0.0
        # 检查查询中是否包含工具关键词
        for keyword in tool.get("keywords", []):
            if keyword.lower() in query_lower:
                score += 0.3
        # 检查应用场景
        if "survival" in query_lower or "生存" in query:
            score += 0.2
        if "cox" in query_lower or "regression" in query_lower or "回归" in query:
            if tool["idname"] == "cox_ph":
                score += 0.5
        if "curve" in query_lower or "km" in query_lower or "曲线" in query:
            if tool["idname"] == "km_curve":
                score += 0.5

        if score > 0:
            matched.append({**tool, "score": min(score, 1.0)})

    # 按分数排序
    matched.sort(key=lambda x: x["score"], reverse=True)

    return {
        "query": query,
        "results": matched[:top_k],
        "collection": "keyword_fallback",
        "count": len(matched[:top_k]),
        "note": "Using keyword matching fallback (vector database unavailable)"
    }
