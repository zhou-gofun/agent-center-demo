#!/usr/bin/env python3
"""
Pipeline Decision Script

Decides when to suggest pipeline composition.
"""
import argparse
import json
import sys
from typing import Dict, List, Any, Optional, Literal


DecisionType = Literal["suggest_pipeline", "continue_questions", "direct_answer"]


# Default thresholds
DEFAULT_SUGGEST_PIPELINE_THRESHOLD = 0.7
DEFAULT_CONTINUE_QUESTIONS_THRESHOLD = 0.4

# Critical information for pipeline creation
CRITICAL_INFO = ["sample_size", "outcome_variables"]

# Sufficient information indicators
SUFFICIENT_INDICATORS = ["grouping_variables", "recommended_methods"]


def check_missing_information(
    features: Dict[str, Any],
    questions: List[Dict[str, str]]
) -> List[str]:
    """Check for critical missing information."""
    missing = []

    if features.get("sample_size") is None:
        missing.append("sample_size")

    for q in questions:
        if q.get("priority") == "high" and q.get("category") == "data_clarification":
            question_lower = q["question"].lower()
            if "sample size" in question_lower and "sample_size" not in missing:
                missing.append("sample_size")
            if "grouping" in question_lower and "grouping_variables" not in missing:
                missing.append("grouping_variables")
            if "outcome" in question_lower and "outcome_variables" not in missing:
                missing.append("outcome_variables")

    return missing


def check_sufficient_information(
    features: Dict[str, Any],
    matches: Dict[str, Any]
) -> bool:
    """Check if there's sufficient information for pipeline creation."""
    has_grouping = bool(features.get("grouping_variables"))
    has_methods = bool(matches.get("recommended_methods"))
    sample_size = features.get("sample_size", 0)
    has_sample = sample_size and sample_size > 0

    has_variables = any(
        len(features.get("variable_types", {}).get(t, [])) > 0
        for t in ["numeric", "categorical", "binary"]
    )

    return (has_grouping or has_methods) and has_sample and has_variables


def make_decision(
    data_features: Dict[str, Any],
    literature_matches: Dict[str, Any],
    generated_questions: List[Dict[str, str]],
    conversation_context: Optional[Dict[str, Any]] = None,
    suggest_pipeline_threshold: float = DEFAULT_SUGGEST_PIPELINE_THRESHOLD,
    continue_questions_threshold: float = DEFAULT_CONTINUE_QUESTIONS_THRESHOLD
) -> Dict[str, Any]:
    """
    Make a decision about whether to suggest pipeline composition.

    Args:
        data_features: Data features from data-analyzer skill
        literature_matches: Literature match results from literature-matcher skill
        generated_questions: Questions from question-generator skill
        conversation_context: Optional conversation history
        suggest_pipeline_threshold: Minimum confidence to suggest pipeline
        continue_questions_threshold: Minimum confidence to continue questions

    Returns:
        Dictionary with decision result
    """
    literature_confidence = literature_matches.get("confidence", 0.0)

    missing_info = check_missing_information(data_features, generated_questions)
    has_sufficient = check_sufficient_information(data_features, literature_matches)
    has_high_priority_questions = any(
        q.get("priority") == "high" for q in generated_questions
    )

    # Decision logic
    if literature_confidence >= suggest_pipeline_threshold and not missing_info:
        return suggest_pipeline_result(data_features, literature_matches)

    elif has_high_priority_questions or missing_info or literature_confidence < continue_questions_threshold:
        return continue_questions_result(
            data_features, literature_matches, generated_questions, missing_info
        )

    else:
        # Moderate confidence - decide based on sufficiency
        if has_sufficient:
            return suggest_pipeline_result(data_features, literature_matches)
        else:
            return continue_questions_result(
                data_features, literature_matches, generated_questions, missing_info
            )


def suggest_pipeline_result(
    features: Dict[str, Any],
    matches: Dict[str, Any]
) -> Dict[str, Any]:
    """Create a 'suggest_pipeline' decision result."""
    confidence = matches.get("confidence", 0.0)
    methods = matches.get("recommended_methods", [])

    study_design = features.get("study_design", "unknown").replace("_", " ")
    grouping = features.get("grouping_variables", [])
    sample_size = features.get("sample_size", 0)

    if grouping and sample_size:
        message = (
            f"Based on your {study_design} study with {sample_size} samples "
            f"and grouping variable(s) like {grouping[0]}, I found relevant analysis methods. "
            f"Would you like me to create a statistical analysis pipeline for you?"
        )
    else:
        message = (
            "Based on your data characteristics and matched literature, "
            "I can help you create a statistical analysis pipeline. "
            "Would you like me to proceed?"
        )

    return {
        "decision": "suggest_pipeline",
        "confidence": confidence,
        "reasoning": (
            f"High literature match confidence ({confidence:.2f}) "
            f"with sufficient data features and recommended methods available."
        ),
        "message": message,
        "suggested_methods": methods,
        "missing_information": [],
    }


def continue_questions_result(
    features: Dict[str, Any],
    matches: Dict[str, Any],
    questions: List[Dict[str, str]],
    missing_info: List[str]
) -> Dict[str, Any]:
    """Create a 'continue_questions' decision result."""
    confidence = matches.get("confidence", 0.0)

    if missing_info:
        reasoning = f"Critical information missing: {', '.join(missing_info)}"
    elif confidence < DEFAULT_CONTINUE_QUESTIONS_THRESHOLD:
        reasoning = f"Low literature match confidence ({confidence:.2f}) - need more context"
    else:
        reasoning = "Additional clarification needed for accurate pipeline recommendation"

    if missing_info:
        message = (
            f"To provide the best analysis recommendation, I need a bit more information. "
            f"Could you help me understand: {', '.join(missing_info)}?"
        )
    else:
        high_priority = [q["question"] for q in questions if q.get("priority") == "high"]
        if high_priority:
            message = (
                "I have a few questions to ensure I recommend the right approach: " +
                high_priority[0]
            )
        else:
            message = "Let me ask a few clarifying questions to provide the best recommendation."

    return {
        "decision": "continue_questions",
        "confidence": confidence,
        "reasoning": reasoning,
        "message": message,
        "suggested_methods": matches.get("recommended_methods", []),
        "missing_information": missing_info,
    }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Decide on pipeline recommendation")
    parser.add_argument("--data-features", type=str, help="JSON string of data features")
    parser.add_argument("--features-file", type=str, help="JSON file with data features")
    parser.add_argument("--literature-matches", type=str, help="JSON string of literature matches")
    parser.add_argument("--matches-file", type=str, help="JSON file with literature matches")
    parser.add_argument("--questions", type=str, help="JSON string of generated questions")
    parser.add_argument("--questions-file", type=str, help="JSON file with generated questions")
    parser.add_argument("--suggest-threshold", type=float, default=DEFAULT_SUGGEST_PIPELINE_THRESHOLD,
                       help="Threshold for suggesting pipeline")
    parser.add_argument("--continue-threshold", type=float, default=DEFAULT_CONTINUE_QUESTIONS_THRESHOLD,
                       help="Threshold for continuing questions")

    args = parser.parse_args()

    data_features = {}
    literature_matches = {}
    generated_questions = []

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
            generated_questions = input_data.get("generated_questions", [])
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

    # Load questions from file/arg if provided
    if args.questions_file:
        with open(args.questions_file, 'r') as f:
            generated_questions = json.load(f)
    elif args.questions:
        generated_questions = json.loads(args.questions)

    result = make_decision(
        data_features=data_features,
        literature_matches=literature_matches,
        generated_questions=generated_questions,
        suggest_pipeline_threshold=args.suggest_threshold,
        continue_questions_threshold=args.continue_threshold
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
