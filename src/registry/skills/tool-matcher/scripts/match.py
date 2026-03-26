#!/usr/bin/env python3
"""
Tool Matcher Script

Matches statistical tools to analysis requirements.
"""
import argparse
import json
import re
import sys
from typing import Dict, List, Any


# Common statistical term mappings
TERM_MAP = {
    "描述性统计": ["描述性统计", "descriptive", "均值", "标准差", "中位数"],
    "组间比较": ["组间比较", "比较", "差异", "group comparison", "t检验", "t检验"],
    "方差分析": ["方差分析", "anova", "多组比较"],
    "卡方": ["卡方", "chi-square", "分类"],
    "回归": ["回归", "regression", "预测"],
    "相关": ["相关", "correlation", "关系"],
    "生存": ["生存", "survival", "kaplan-meier"],
    "可视化": ["图", "plot", "可视化", "图表"],
    "正态": ["正态", "normality"],
}


def match_tools(query: str, top_k: int = 10, use_vector: bool = False) -> Dict[str, Any]:
    """
    Match statistical tools based on query.

    Args:
        query: User's analysis question or requirement
        top_k: Number of results to return
        use_vector: Whether to use vector search (default: False)

    Returns:
        Match results dictionary
    """
    if not query:
        return {
            "matched_tools": [],
            "requirements_analysis": {
                "query": query,
                "found_tools": 0,
                "search_method": "none"
            },
            "error": "Missing query"
        }

    # Use keyword matching by default (faster, no ONNX dependency)
    if not use_vector:
        keyword_results = search_with_keywords(query, top_k)
        return {
            "matched_tools": keyword_results,
            "requirements_analysis": {
                "query": query,
                "found_tools": len(keyword_results),
                "search_method": "keyword_matching"
            }
        }

    # Vector search (optional, requires ChromaDB)
    return search_with_vector(query, top_k)


def search_with_keywords(query: str, top_k: int) -> List[Dict[str, Any]]:
    """Search tools using keyword matching."""
    try:
        from src.vector_db.data_loader import get_assembly_loader

        loader = get_assembly_loader()
        df = loader.load()

        # Extract search terms
        search_terms = extract_search_terms(query)

        # Calculate scores for each tool
        scores = []
        for _, row in df.iterrows():
            score = 0.0
            toolname = str(row.get('toolname', ''))
            keywords = str(row.get('keywords', ''))
            applications = str(row.get('applications', ''))
            description = str(row.get('description', ''))

            # Combine all text fields
            all_text = f"{toolname} {keywords} {applications} {description}".lower()

            # Calculate match score
            for term in search_terms:
                if term in toolname.lower():
                    score += 3.0  # Tool name match has highest weight
                if term in keywords.lower():
                    score += 2.0  # Keyword match
                if term in applications.lower():
                    score += 1.0  # Application match
                if term in description.lower():
                    score += 0.5  # Description match

            if score > 0:
                scores.append({
                    "toolid": int(row.get('toolid', 0)),
                    "toolname": toolname,
                    "idname": str(row.get('idname', '')),
                    "relevance_score": min(score / len(search_terms), 1.0),
                    "match_reason": f"关键词匹配: {', '.join(search_terms)}",
                    "keywords": keywords,
                    "applications": applications,
                    "conditions": str(row.get('conditions', ''))
                })

        # Sort by score and return top_k
        scores.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scores[:top_k]

    except Exception as e:
        print(f"Error in keyword search: {e}", file=sys.stderr)
        return []


def search_with_vector(query: str, top_k: int) -> Dict[str, Any]:
    """Search tools using vector semantic search."""
    try:
        from src.registry.skills.semantic_search.scripts.search import semantic_search

        result = semantic_search(query, collection="assembly_tools", top_k=top_k)

        # Transform results to match tool-matcher format
        matched_tools = []
        for r in result.get("results", []):
            matched_tools.append({
                "toolid": r.get("toolid"),
                "toolname": r.get("toolname"),
                "idname": r.get("idname"),
                "relevance_score": r.get("score", 0.0),
                "match_reason": f"语义搜索匹配 (score: {r.get('score', 0.0):.2f})",
                "description": r.get("description", ""),
            })

        return {
            "matched_tools": matched_tools,
            "requirements_analysis": {
                "query": query,
                "found_tools": len(matched_tools),
                "search_method": "vector_search"
            }
        }
    except Exception as e:
        return {
            "matched_tools": [],
            "requirements_analysis": {
                "query": query,
                "found_tools": 0,
                "search_method": "vector_search"
            },
            "error": str(e)
        }


def extract_search_terms(query: str) -> List[str]:
    """Extract search terms from query."""
    query_lower = query.lower()
    terms = []

    # Check for known terms
    for key, values in TERM_MAP.items():
        if key in query_lower or any(v in query_lower for v in values):
            terms.extend([key] + values[:2])  # Add main term and first 2 synonyms

    # Extract other keywords from query
    words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', query)
    terms.extend([w for w in words if len(w) >= 2])

    return list(set(terms))  # Deduplicate


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Match statistical tools to requirements")
    parser.add_argument("--query", type=str, help="Analysis query or requirement")
    parser.add_argument("--top-k", type=int, default=10, help="Number of results (default: 10)")
    parser.add_argument("--use-vector", action="store_true", help="Use vector search instead of keywords")

    args = parser.parse_args()

    if not args.query:
        args.query = sys.stdin.read().strip()

    result = match_tools(args.query, args.top_k, args.use_vector)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
