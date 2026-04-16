"""Tests for StudentMemory class."""
import pytest
import json
import tempfile
from pathlib import Path
from datetime import date, timedelta


def _make_memory(tmp_path):
    from backend.state.student_memory import StudentMemory
    return StudentMemory(tmp_path)


def test_init_creates_files(tmp_path):
    mem = _make_memory(tmp_path)
    assert (tmp_path / "student_memory" / "quiz_log.json").exists()
    assert (tmp_path / "student_memory" / "topic_mastery.json").exists()
    assert (tmp_path / "student_memory" / "skill_profile.json").exists()
    assert (tmp_path / "student_memory" / "weak_areas.json").exists()
    assert (tmp_path / "student_memory" / "evolution_log.json").exists()
    assert (tmp_path / "student_memory" / "answer_history.json").exists()


def test_log_quiz_answer_and_seen(tmp_path):
    mem = _make_memory(tmp_path)
    mem.log_quiz_answer(
        quiz_id="q1", quiz_type="topic_quiz", subject="math", chapter=4,
        topic="Quadratic Equations", question_id="math_ch4_001",
        question_text="Solve x²-5x+6=0", question_type="SA", marks=3,
        concepts_tested=["factorization"], bloom_level="apply",
        skill_tags=["procedural_fluency"], student_answer="x=2,3",
        correct_answer="x=2 and x=3", is_correct=True, is_partial=False,
        feedback="Correct!", conceptual_gap=None, answer_mode="text",
        time_taken_seconds=90
    )
    assert mem.has_student_seen_question("math_ch4_001")
    assert not mem.has_student_seen_question("math_ch4_999")


def test_get_student_context(tmp_path):
    mem = _make_memory(tmp_path)
    ctx = mem.get_student_context_for_quiz("math", 4, "Quadratic Equations")
    assert "mastery_score" in ctx
    assert "questions_seen_ids" in ctx
    assert "weak_concepts" in ctx
    assert isinstance(ctx["mastery_score"], (int, float))


def test_topic_mastery_updates(tmp_path):
    mem = _make_memory(tmp_path)
    for i in range(4):
        mem.log_quiz_answer(
            quiz_id="q1", quiz_type="topic_quiz", subject="math", chapter=4,
            topic="Quadratic Equations", question_id=f"math_ch4_00{i}",
            question_text="Q", question_type="MCQ", marks=1,
            concepts_tested=["roots"], bloom_level="apply",
            skill_tags=["quantitative"], student_answer="A",
            correct_answer="A", is_correct=True, is_partial=False,
            feedback="Good", conceptual_gap=None, answer_mode="text",
            time_taken_seconds=30
        )
    ctx = mem.get_student_context_for_quiz("math", 4, "Quadratic Equations")
    assert ctx["mastery_score"] > 50


def test_weak_areas_flagged(tmp_path):
    mem = _make_memory(tmp_path)
    mem.flag_weak_areas([{
        "concept": "completing_the_square",
        "reason": "Failed 2/2 questions",
        "priority": 8,
        "next_review_date": (date.today() + timedelta(days=1)).isoformat(),
        "subject": "math",
        "chapter": 4,
        "topic": "Quadratic Equations"
    }])
    areas = mem.get_weak_areas()
    assert len(areas) == 1
    assert areas[0]["concept"] == "completing_the_square"


def test_mark_concept_strong(tmp_path):
    mem = _make_memory(tmp_path)
    mem.flag_weak_areas([{
        "concept": "roots",
        "reason": "Failed",
        "priority": 5,
        "next_review_date": date.today().isoformat(),
        "subject": "math",
        "chapter": 4,
        "topic": "Quadratic Equations"
    }])
    mem.mark_concept_strong("math", 4, "Quadratic Equations", "roots")
    areas = mem.get_weak_areas()
    assert not any(a["concept"] == "roots" for a in areas)


def test_get_revision_recommendations(tmp_path):
    mem = _make_memory(tmp_path)
    from datetime import date, timedelta
    mem.flag_weak_areas([
        {"concept": "HCF", "reason": "Failed", "priority": 9,
         "next_review_date": (date.today() - timedelta(days=1)).isoformat(),
         "subject": "math", "chapter": 1, "topic": "Real Numbers"},
        {"concept": "LCM", "reason": "Failed", "priority": 5,
         "next_review_date": (date.today() + timedelta(days=3)).isoformat(),
         "subject": "math", "chapter": 1, "topic": "Real Numbers"},
    ])
    recs = mem.get_revision_recommendations(n=1)
    assert len(recs) == 1
    assert recs[0]["concept"] == "HCF"
