"""Tests for QuestionEvaluator — bank-first selection."""
import pytest
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def _make_evaluator():
    from backend.ai.question_evaluator import QuestionEvaluator
    return QuestionEvaluator(DATA_DIR)


def test_evaluator_loads_indices():
    ev = _make_evaluator()
    assert ev.qb_index  # NCERT bank index loaded
    assert ev.nb_index  # Novel bank index loaded


def test_keyword_matching_math():
    ev = _make_evaluator()
    chapters = ev._match_keywords_to_chapters("quadratic equations", "math")
    assert len(chapters) > 0
    assert any(c == 4 for c in chapters)


def test_score_question_dimensions():
    ev = _make_evaluator()
    question = {
        "id": "test_q1",
        "type": "MCQ",
        "difficulty": "medium",
        "bloom_level": "apply",
        "concepts": ["quadratic_formula"],
        "skill_tags": ["procedural_fluency"],
        "marks": 1,
    }
    student_ctx = {
        "mastery_score": 50,
        "bloom_level_reached": "apply",
        "questions_seen_ids": [],
        "weak_concepts": [],
        "strong_concepts": [],
    }
    score = ev._score_question(
        question, "topic_quiz", student_ctx, "Quadratic Equations", {}
    )
    assert 0.0 <= score <= 1.0


def test_bank_questions_loaded_for_math_ch4():
    ev = _make_evaluator()
    candidates = ev._load_bank_questions("math", [4])
    assert len(candidates) > 0
    for q in candidates:
        assert "question_text" in q or "id" in q


def test_no_seen_questions_in_result(tmp_path):
    """Questions already seen should be filtered out — when all seen, generation flagged."""
    ev = _make_evaluator()
    all_qs = ev._load_bank_questions("math", [4])
    all_ids = [q.get("id", "") for q in all_qs if q.get("id")]

    student_ctx = {
        "mastery_score": 50,
        "bloom_level_reached": "apply",
        "questions_seen_ids": all_ids,
        "weak_concepts": [],
        "strong_concepts": [],
    }
    result = ev.evaluate_and_select(
        quiz_type="topic_quiz",
        subject="math",
        chapter=4,
        topic="Quadratic Equations",
        student_context=student_ctx,
    )
    assert "questions" in result
    assert "quiz_id" in result
    # All seen IDs should not appear in result
    result_ids = [q.get("id", "") for q in result["questions"] if q.get("id")]
    assert not any(rid in all_ids for rid in result_ids)
