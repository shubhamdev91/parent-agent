"""Tests for SkillExtractor — no Gemini calls."""
import pytest

SAMPLE_QUIZ_INPUT = {
    "quiz_id": "q_test_1",
    "quiz_type": "topic_quiz",
    "subject": "math",
    "chapter": 4,
    "topic": "Quadratic Equations",
    "questions_evaluated": [
        {
            "question_id": "q1", "question_type": "MCQ", "marks": 1,
            "score_awarded": 1, "is_correct": True,
            "concepts_tested": ["quadratic_formula"], "bloom_level": "apply",
            "skill_tags": ["procedural_fluency"], "conceptual_gap": None,
            "suggest_re_practice": False
        },
        {
            "question_id": "q2", "question_type": "SA", "marks": 3,
            "score_awarded": 0, "is_correct": False,
            "concepts_tested": ["completing_the_square"], "bloom_level": "apply",
            "skill_tags": ["analytical"], "conceptual_gap": "Confused sign rules",
            "suggest_re_practice": True
        },
    ],
    "total_score": 1,
    "max_score": 4,
}

SKILL_PROFILE = {
    "current_scores": {
        "quantitative": 70, "analytical": 65, "logical_reasoning": 55,
        "conceptual_understanding": 78, "scientific_reasoning": 65,
        "procedural_fluency": 80, "problem_solving": 62
    }
}


def test_build_extraction_prompt():
    from backend.ai.skill_extractor import build_extraction_prompt
    prompt = build_extraction_prompt(SAMPLE_QUIZ_INPUT, SKILL_PROFILE, {})
    assert "procedural_fluency" in prompt
    assert "Quadratic Equations" in prompt


def test_mock_extraction_schema():
    from backend.ai.skill_extractor import _build_mock_extraction
    result = _build_mock_extraction(SAMPLE_QUIZ_INPUT, SKILL_PROFILE)
    assert "skill_updates" in result
    assert "topic_mastery_update" in result
    assert "weak_areas_flagged" in result
    assert "evolution_note" in result
    for skill in SKILL_PROFILE["current_scores"]:
        assert skill in result["skill_updates"]


def test_weak_areas_from_failed_questions():
    from backend.ai.skill_extractor import _build_mock_extraction
    result = _build_mock_extraction(SAMPLE_QUIZ_INPUT, SKILL_PROFILE)
    concepts = [w["concept"] for w in result["weak_areas_flagged"]]
    assert "completing_the_square" in concepts


def test_topic_mastery_update_structure():
    from backend.ai.skill_extractor import _build_mock_extraction
    result = _build_mock_extraction(SAMPLE_QUIZ_INPUT, SKILL_PROFILE)
    update = result["topic_mastery_update"]
    assert "topic" in update
    assert "new_mastery" in update
    assert "trend" in update
    assert update["topic"] == "Quadratic Equations"
