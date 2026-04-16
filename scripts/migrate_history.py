"""Populate student_memory from existing child_profile.json quiz history."""

import json
import uuid
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.state.student_memory import StudentMemory


def migrate_quiz_history():
    profile_path = Path("data/child_profile.json")
    mem = StudentMemory(Path("data"))

    with open(profile_path, encoding="utf-8") as f:
        profile = json.load(f)

    quiz_history = profile.get("quiz_history", [])
    topic_history = profile.get("topic_history", [])

    print(f"Found {len(quiz_history)} quizzes and {len(topic_history)} topics to migrate.")

    for quiz in quiz_history:
        topic_id = quiz.get("topic_id", "")
        topic_entry = next((t for t in topic_history if t.get("id") == topic_id), None)
        if not topic_entry:
            continue

        subject = topic_entry.get("subject", "math")
        chapter_str = topic_entry.get("chapter", "1")
        # Extract chapter number from string like "4. Quadratic Equations"
        try:
            chapter_num = int(str(chapter_str).split(".")[0].strip())
        except (ValueError, IndexError):
            chapter_num = 1
        topic = topic_entry.get("topic", "Unknown")

        quiz_id = quiz.get("id", str(uuid.uuid4()))
        details = quiz.get("details", [])

        for i, detail in enumerate(details):
            question_text = detail.get("question", "")
            is_correct = detail.get("correct", False)
            student_ans = detail.get("student_answer", "")
            correct_ans = detail.get("correct_answer", detail.get("answer", ""))

            mem.log_quiz_answer(
                quiz_id=quiz_id,
                quiz_type="topic_quiz",
                subject=subject,
                chapter=chapter_num,
                topic=topic,
                question_id=f"migrated_{quiz_id}_{i}",
                question_text=question_text,
                question_type="MCQ",
                marks=1,
                concepts_tested=[],
                bloom_level="apply",
                skill_tags=[],
                student_answer=str(student_ans),
                correct_answer=str(correct_ans),
                is_correct=bool(is_correct),
                is_partial=False,
                feedback=detail.get("feedback", ""),
                conceptual_gap=None,
                answer_mode="text",
                time_taken_seconds=60
            )

    print("Migration complete.")
    mem_dir = Path("data/student_memory")
    ah = json.loads((mem_dir / "answer_history.json").read_text())
    tm = json.loads((mem_dir / "topic_mastery.json").read_text())
    print(f"  answer_history: {len(ah['answers'])} entries")
    print(f"  topic_mastery: {len(tm['topics'])} topics")


if __name__ == "__main__":
    migrate_quiz_history()
