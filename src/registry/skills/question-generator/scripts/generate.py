#!/usr/bin/env python3
"""
Question Generator Script

Generates follow-up questions based on data analysis context.
"""
import argparse
import json
import sys
from typing import Dict, List, Any, Optional


def generate_questions(
    data_features: Dict[str, Any],
    literature_matches: Dict[str, Any],
    query: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    Generate follow-up questions based on context.

    Args:
        data_features: Data features from data-analyzer skill
        literature_matches: Literature match results from literature-matcher skill
        query: Original user query

    Returns:
        List of question dictionaries
    """
    questions = []

    # Data clarification questions
    questions.extend(get_data_clarification_questions(data_features))

    # Analysis goal questions
    questions.extend(get_analysis_goal_questions(data_features, query))

    # Method preference questions
    questions.extend(get_method_preference_questions(data_features, literature_matches))

    # Literature-specific questions
    questions.extend(get_literature_questions(literature_matches))

    # Deduplicate and prioritize
    return prioritize_questions(deduplicate_questions(questions))


def get_data_clarification_questions(features: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate data clarification questions."""
    questions = []

    # Sample size
    if features.get("sample_size") is None:
        questions.append({
            "question": "What is the sample size of your dataset?",
            "rationale": "Sample size is needed to determine appropriate statistical methods.",
            "category": "data_clarification",
            "priority": "high"
        })

    # Grouping variables
    if len(features.get("grouping_variables", [])) == 0:
        questions.append({
            "question": "Are there any grouping or comparison variables in your data?",
            "rationale": "Grouping variables are important for selecting comparison tests.",
            "category": "data_clarification",
            "priority": "medium"
        })

    # Study design
    if features.get("study_design") == "unknown":
        questions.append({
            "question": "What type of study design does this data come from (e.g., RCT, cohort, case-control)?",
            "rationale": "Study design influences the choice of statistical methods.",
            "category": "data_clarification",
            "priority": "medium"
        })

    return questions


def get_analysis_goal_questions(
    features: Dict[str, Any],
    query: Optional[str]
) -> List[Dict[str, str]]:
    """Generate analysis goal questions."""
    questions = []

    # Primary research question (always ask)
    questions.append({
        "question": "What is your primary research question or hypothesis?",
        "rationale": "Understanding the research goal helps recommend the most relevant analysis methods.",
        "category": "analysis_goals",
        "priority": "high"
    })

    # Comparison vs relationship
    if len(features.get("grouping_variables", [])) > 0:
        questions.append({
            "question": "Do you want to compare groups or examine relationships between variables?",
            "rationale": "This distinction determines whether to use comparison tests or correlation/regression methods.",
            "category": "analysis_goals",
            "priority": "high"
        })

    # Query-specific questions
    if query:
        if any(word in query.lower() for word in ["compare", "difference", "between"]):
            if len(features.get("grouping_variables", [])) == 0:
                questions.append({
                    "question": "Which variable defines the groups you want to compare?",
                    "rationale": "Comparison tests require a grouping variable.",
                    "category": "analysis_goals",
                    "priority": "high"
                })

    return questions


def get_method_preference_questions(
    features: Dict[str, Any],
    matches: Dict[str, Any]
) -> List[Dict[str, str]]:
    """Generate method preference questions."""
    questions = []

    # Multiple methods available
    if len(matches.get("recommended_methods", [])) > 2:
        questions.append({
            "question": "Do you have preferences for specific statistical methods?",
            "rationale": "Multiple methods may be applicable; preferences can narrow recommendations.",
            "category": "method_preferences",
            "priority": "low"
        })

    # Small sample size
    if features.get("sample_size", 0) < 50:
        questions.append({
            "question": "Would you consider non-parametric methods given the small sample size?",
            "rationale": "Non-parametric tests are often more appropriate for small samples.",
            "category": "method_preferences",
            "priority": "medium"
        })

    # t-test vs ANOVA
    recommended = matches.get("recommended_methods", [])
    if "t_test" in recommended and "anova" in recommended:
        questions.append({
            "question": "Do you have exactly two groups to compare, or more than two?",
            "rationale": "This determines whether a t-test or ANOVA is more appropriate.",
            "category": "method_preferences",
            "priority": "high"
        })

    return questions


def get_literature_questions(matches: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate questions based on literature matches."""
    questions = []
    confidence = matches.get("confidence", 0.0)

    # High confidence - suggest specific methods
    if confidence > 0.7:
        methods = matches.get("recommended_methods", [])[:3]
        if methods:
            methods_str = ", ".join(m.replace("_", " ") for m in methods)
            questions.append({
                "question": f"Would you like me to help you set up analysis using methods like {methods_str}?",
                "rationale": "These methods were commonly used in similar studies.",
                "category": "method_preferences",
                "priority": "medium"
            })

    # Literature examples available
    if matches.get("matches"):
        questions.append({
            "question": "Would you like to see the specific methods used in similar studies?",
            "rationale": "Literature examples can provide validated analysis approaches.",
            "category": "validation",
            "priority": "low"
        })

    return questions


def deduplicate_questions(questions: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Remove duplicate questions."""
    seen = set()
    unique = []
    for q in questions:
        question_text = q["question"]
        if question_text not in seen:
            seen.add(question_text)
            unique.append(q)
    return unique


def prioritize_questions(questions: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Sort questions by priority."""
    priority_order = {"high": 0, "medium": 1, "low": 2}
    return sorted(questions, key=lambda q: priority_order.get(q["priority"], 1))


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Generate follow-up questions")
    parser.add_argument("--data-features", type=str, help="JSON string of data features")
    parser.add_argument("--features-file", type=str, help="JSON file with data features")
    parser.add_argument("--literature-matches", type=str, help="JSON string of literature matches")
    parser.add_argument("--matches-file", type=str, help="JSON file with literature matches")
    parser.add_argument("--query", type=str, help="User query")

    args = parser.parse_args()

    data_features = {}
    literature_matches = {}
    query = args.query

    # Try to read JSON input from stdin first (for skill execution)
    stdin_data = sys.stdin.read().strip()
    if stdin_data:
        try:
            input_data = json.loads(stdin_data)
            # Check if it's the UniversalScriptExecutor format
            if "__entrypoint__" in input_data:
                input_data = input_data["__input__"]
            data_features = input_data.get("data_features", {})
            literature_matches = input_data.get("literature_matches", {})
            if not query:
                query = input_data.get("query")
        except json.JSONDecodeError:
            pass

    # Load data features from file/arg if provided
    if args.features_file:
        with open(args.features_file, 'r') as f:
            data_features = json.load(f)
    elif args.data_features:
        data_features = json.loads(args.data_features)

    # Load literature matches from file/arg if provided
    if args.matches_file:
        with open(args.matches_file, 'r') as f:
            literature_matches = json.load(f)
    elif args.literature_matches:
        literature_matches = json.loads(args.literature_matches)

    result = generate_questions(data_features, literature_matches, query)
    print(json.dumps({"questions": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
