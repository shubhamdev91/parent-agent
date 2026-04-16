"""Tests for AnswerEvaluatorV2 — prompt building and schema validation (no Gemini calls)."""
import pytest

SAMPLE_QUESTION = {
    "id": "math_ch4_001",
    "question_text": "Find the roots of x² - 5x + 6 = 0",
    "type": "SA",
    "correct_answer": "The roots are x = 2 and x = 3",
    "explanation": "By factorization: (x-2)(x-3)=0",
    "concepts": ["quadratic_factorization", "roots"],
    "bloom_level": "apply",
    "skill_tags": ["procedural_fluency"],
    "marks": 3
}

STUDENT_CTX = {
    "mastery_score": 65,
    "previous_attempts_on_concept": []
}


def test_evaluation_prompt_contains_question():
    from backend.ai.answer_evaluator_v2 import build_evaluation_prompt
    prompt = build_evaluation_prompt(
        question=SAMPLE_QUESTION,
        student_answer={"mode": "text", "raw_input": "x = 2 and x = 3"},
        student_context=STUDENT_CTX
    )
    assert "x² - 5x + 6" in prompt
    assert "x = 2 and x = 3" in prompt
    assert "CBSE" in prompt


def test_mock_evaluation_schema():
    """The mock evaluation dict must have all required keys."""
    from backend.ai.answer_evaluator_v2 import _build_mock_evaluation
    result = _build_mock_evaluation(is_correct=True, marks=3)
    required = [
        "is_correct", "is_partial", "score_awarded", "feedback",
        "correct_answer_display", "conceptual_gap", "mom_feedback",
        "suggest_re_practice", "avatar_emotion", "cbse_marking_notes"
    ]
    for key in required:
        assert key in result, f"Missing key: {key}"


def test_mock_correct_emotion():
    from backend.ai.answer_evaluator_v2 import _build_mock_evaluation
    result = _build_mock_evaluation(is_correct=True, marks=1)
    assert result["avatar_emotion"] in ["happy", "celebrating"]
    assert result["is_correct"] is True
    assert result["score_awarded"] == 1


def test_mock_wrong_emotion():
    from backend.ai.answer_evaluator_v2 import _build_mock_evaluation
    result = _build_mock_evaluation(is_correct=False, marks=1)
    assert result["avatar_emotion"] in ["encouraging", "concerned"]
    assert result["is_correct"] is False
    assert result["score_awarded"] == 0


def test_ocr_prompt_contains_question():
    from backend.ai.answer_evaluator_v2 import build_ocr_prompt
    prompt = build_ocr_prompt(SAMPLE_QUESTION)
    assert SAMPLE_QUESTION["question_text"] in prompt
    assert str(SAMPLE_QUESTION["marks"]) in prompt
