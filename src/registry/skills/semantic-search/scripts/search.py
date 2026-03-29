#!/usr/bin/env python3
"""
Semantic Search Script

Performs vector semantic search on knowledge bases.
"""
import argparse
import json
import sys
from typing import Dict, List, Any, Optional


def semantic_search(
    query: str,
    collection: str = "assembly_tools",
    top_k: int = 10
) -> Dict[str, Any]:
    """
    Perform semantic search on the vector database.

    Args:
        query: Search query
        collection: Target collection name (default: assembly_tools)
        top_k: Number of results to return

    Returns:
        Search results dictionary
    """
    if not query:
        return {
            "query": query,
            "results": [],
            "error": "Missing query"
        }

    try:
        from vector_db.chroma_store import get_vector_store

        db = get_vector_store()
        collections = db.list_collections()

        # If specific collection requested and it exists
        if collection and collection in collections:
            results = db.search(collection, query, top_k=top_k)
            return {
                "query": query,
                "results": [_format_result(r) for r in results],
                "collection": collection,
                "count": len(results)
            }

        # Search all collections
        all_results = []
        for coll_name in collections:
            try:
                results = db.search(coll_name, query, top_k=top_k)
                for r in results:
                    r["collection"] = coll_name
                    all_results.append(r)
            except Exception as e:
                print(f"Warning: Search in {coll_name} failed: {e}", file=sys.stderr)

        # Sort by score and return top_k
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        all_results = all_results[:top_k]

        return {
            "query": query,
            "results": [_format_result(r) for r in all_results],
            "collections_searched": collections,
            "count": len(all_results)
        }

    except Exception as e:
        return {
            "query": query,
            "results": [],
            "error": str(e)
        }


def _format_result(result: Dict) -> Dict:
    """Format search result for output."""
    metadata = result.get("metadata", {})

    return {
        "id": result.get("id"),
        "collection": result.get("collection"),
        "toolid": metadata.get("toolid"),
        "toolname": metadata.get("toolname", ""),
        "idname": metadata.get("idname", ""),
        "description": metadata.get("description", ""),
        "score": result.get("score", 0.0),
        "metadata": metadata
    }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Semantic search on knowledge bases")
    parser.add_argument("--query", type=str, help="Search query")
    parser.add_argument("--collection", type=str, default="assembly_tools",
                       help="Target collection (default: assembly_tools)")
    parser.add_argument("--top-k", type=int, default=10,
                       help="Number of results (default: 10)")

    args = parser.parse_args()

    # Try to read JSON input from stdin first (for skill execution)
    stdin_data = sys.stdin.read().strip()
    if stdin_data:
        try:
            input_data = json.loads(stdin_data)
            # Check if it's the UniversalScriptExecutor format
            if "__entrypoint__" in input_data:
                args.query = input_data["__input__"].get("query", args.query or "")
                args.collection = input_data["__input__"].get("collection", args.collection)
                args.top_k = input_data["__input__"].get("top_k", args.top_k)
            else:
                # Direct JSON input
                args.query = input_data.get("query", args.query or "")
                args.collection = input_data.get("collection", args.collection)
                args.top_k = input_data.get("top_k", args.top_k)
        except json.JSONDecodeError:
            # Not JSON, treat as plain text query
            if not args.query:
                args.query = stdin_data

    if not args.query:
        parser.error("--query is required or provide via stdin")

    result = semantic_search(args.query, args.collection, args.top_k)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
