#!/usr/bin/env python3
"""
Literature Matcher Script

Matches medical literature based on data features.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional


# Method keywords for matching
METHOD_KEYWORDS = {
    "t_test": ["t-test", "t test", "students t", "independent t"],
    "paired_t_test": ["paired t-test", "paired t test", "dependent t"],
    "anova": ["anova", "analysis of variance", "f-test"],
    "ancova": ["ancova", "analysis of covariance"],
    "chi_square": ["chi-square", "chi square", "χ2", "chisquare"],
    "fisher_exact": ["fisher exact", "fisher's exact"],
    "mann_whitney": ["mann-whitney", "wilcoxon rank sum", "mann whitney"],
    "wilcoxon": ["wilcoxon signed-rank", "wilcoxon signed rank"],
    "kruskal_wallis": ["kruskal-wallis", "kruskal wallis"],
    "regression": ["regression", "linear regression", "logistic regression"],
    "logistic": ["logistic regression", "logit", "logistic model"],
    "survival": ["survival analysis", "kaplan-meier", "cox regression", "cox proportional"],
    "correlation": ["correlation", "pearson", "spearman"],
    "mixed_model": ["mixed model", "lmm", "linear mixed model", "multilevel"],
    "mcmc": ["mcmc", "markov chain", "bayesian", "bayes"],
}

# Study design mappings
STUDY_DESIGN_METHODS = {
    "randomized_controlled_trial": ["t_test", "anova", "ancova", "mixed_model"],
    "cohort_study": ["survival", "regression", "logistic"],
    "case_control": ["chi_square", "fisher_exact", "logistic"],
    "cross_sectional": ["chi_square", "correlation", "regression"],
    "meta_analysis": ["mcmc", "regression"],
}


def find_database(db_path: Optional[str] = None) -> Optional[str]:
    """Find the literature database file."""
    if db_path and os.path.exists(db_path):
        return db_path

    default_paths = [
        "pmcids_list.get.methods.filter(1).xlsx",
        "data/pmcids_list.get.methods.filter(1).xlsx",
        "src/data/pmcids_list.get.methods.filter(1).xlsx",
        "database/pmcids_list.get.methods.filter(1).xlsx",
    ]

    for path in default_paths:
        if os.path.exists(path):
            return path

    cwd = Path.cwd()
    for root in [cwd, cwd / "src", cwd.parent]:
        for path in default_paths:
            full_path = root / path
            if full_path.exists():
                return str(full_path)

    return None


def load_database(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load the literature database."""
    path = find_database(db_path)
    if not path:
        return []

    try:
        import pandas as pd
        df = pd.read_excel(path)
        return df.to_dict('records')
    except ImportError:
        print("Warning: pandas not available for literature database", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Warning: Error loading literature database: {e}", file=sys.stderr)
        return []


def score_methods(
    study_design: str,
    variable_types: Dict[str, List[str]],
    grouping_vars: List[str],
    sample_size: Optional[int],
    query: Optional[str]
) -> Dict[str, float]:
    """Score analysis methods based on features."""
    scores = {method: 0.0 for method in METHOD_KEYWORDS.keys()}

    # Study design bonus
    design_methods = STUDY_DESIGN_METHODS.get(study_design, [])
    for method in design_methods:
        scores[method] += 0.3

    # Grouping variables suggest comparison tests
    if grouping_vars:
        has_numeric = any(variable_types.get("numeric", []))
        has_categorical = any(variable_types.get("categorical", []))

        if has_numeric:
            scores["t_test"] += 0.4
            scores["anova"] += 0.3
            scores["mann_whitney"] += 0.2

        if has_categorical:
            scores["chi_square"] += 0.4
            scores["fisher_exact"] += 0.3

    # Sample size considerations
    if sample_size and sample_size < 30:
        scores["mann_whitney"] += 0.2
        scores["wilcoxon"] += 0.2

    # Query keyword matching
    if query:
        query_lower = query.lower()
        for method, keywords in METHOD_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    scores[method] += 0.2

    return scores


def search_database(
    database: List[Dict[str, Any]],
    data_features: Dict[str, Any],
    query: Optional[str],
    method_scores: Dict[str, float],
    match_threshold: float = 0.5
) -> List[Dict[str, Any]]:
    """Search database for matching literature."""
    matches = []

    for entry in database:
        score = 0.0
        entry_str = str(entry).lower()

        # Study design match
        study_design = data_features.get("study_design", "")
        if study_design != "unknown" and study_design in entry_str:
            score += 0.3

        # Method keywords match
        matched_methods = []
        for method, keywords in METHOD_KEYWORDS.items():
            for keyword in keywords:
                if keyword in entry_str:
                    score += 0.1 * method_scores.get(method, 0.5)
                    if method not in matched_methods:
                        matched_methods.append(method)

        # Query match
        if query:
            query_words = set(query.lower().split())
            entry_words = set(entry_str.split())
            overlap = len(query_words & entry_words)
            if query_words:
                score += 0.2 * (overlap / len(query_words))

        if score >= match_threshold:
            matches.append({
                "pmcid": entry.get("pmcid", entry.get("PMCID", "")),
                "title": entry.get("title", entry.get("Title", "Unknown")),
                "relevance_score": min(score, 1.0),
                "methods": matched_methods,
                "study_design": entry.get("study_design", ""),
                "abstract": entry.get("abstract", entry.get("Abstract", ""))[:200],
            })

    matches.sort(key=lambda x: x["relevance_score"], reverse=True)
    return matches[:10]


def create_synthetic_matches(method_scores: Dict[str, float]) -> List[Dict[str, Any]]:
    """Create synthetic matches when database is unavailable."""
    matches = []

    sorted_methods = sorted(method_scores.items(), key=lambda x: x[1], reverse=True)[:5]

    for method, score in sorted_methods:
        if score > 0:
            keywords = METHOD_KEYWORDS.get(method, [])
            keyword_str = ", ".join(keywords[:2])

            matches.append({
                "pmcid": f"SYNTHETIC_{method.upper()}",
                "title": f"Statistical method: {method.replace('_', ' ').title()} ({keyword_str})",
                "relevance_score": min(score + 0.3, 1.0),
                "methods": [method],
                "study_design": "various",
                "abstract": f"Recommended for studies with these characteristics. Keywords: {keyword_str}",
            })

    return matches


def match_literature(
    data_features: Dict[str, Any],
    query: Optional[str] = None,
    db_path: Optional[str] = None,
    match_threshold: float = 0.5
) -> Dict[str, Any]:
    """
    Match literature based on data features.

    Args:
        data_features: Data features from data-analyzer skill
        query: Optional user query or analysis goal
        db_path: Optional path to literature database
        match_threshold: Minimum relevance score for matches

    Returns:
        Dictionary with match results
    """
    study_design = data_features.get("study_design", "unknown")
    variable_types = data_features.get("variable_types", {})
    grouping_vars = data_features.get("grouping_variables", [])
    sample_size = data_features.get("sample_size")

    # Calculate method scores
    method_scores = score_methods(study_design, variable_types, grouping_vars, sample_size, query)

    # Try to load and search database
    database = load_database(db_path)

    if database:
        matches = search_database(database, data_features, query, method_scores, match_threshold)
        recommended_methods = []
        for match in matches:
            if match["relevance_score"] >= match_threshold:
                for method in match["methods"]:
                    if method not in recommended_methods:
                        recommended_methods.append(method)

        confidence = max([m["relevance_score"] for m in matches], default=0.0)

        return {
            "matches": matches,
            "recommended_methods": recommended_methods,
            "confidence": confidence,
            "total_searched": len(database),
        }
    else:
        # Fallback to synthetic matches
        matches = create_synthetic_matches(method_scores)
        sorted_methods = sorted(method_scores.items(), key=lambda x: x[1], reverse=True)
        recommended_methods = [m[0] for m in sorted_methods if m[1] > 0][:5]
        confidence = max(method_scores.values()) if method_scores else 0.0

        return {
            "matches": matches,
            "recommended_methods": recommended_methods,
            "confidence": confidence,
            "total_searched": 0,
        }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Match literature to data features")
    parser.add_argument("--data-features", type=str, help="JSON string of data features")
    parser.add_argument("--file", type=str, help="JSON file with data features")
    parser.add_argument("--query", type=str, help="User query or analysis goal")
    parser.add_argument("--db-path", type=str, help="Path to literature database")
    parser.add_argument("--threshold", type=float, default=0.5, help="Match threshold")

    args = parser.parse_args()

    if args.file:
        with open(args.file, 'r') as f:
            data_features = json.load(f)
    elif args.data_features:
        data_features = json.loads(args.data_features)
    else:
        data_features = json.loads(sys.stdin.read())

    result = match_literature(data_features, args.query, args.db_path, args.threshold)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
