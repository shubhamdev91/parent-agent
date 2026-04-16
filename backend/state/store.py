"""State store — reads/writes child profile and topic history from JSON."""

import json
import uuid
from datetime import date
from pathlib import Path
from typing import Optional
from backend.config import CHILD_PROFILE_PATH, MATH_CHAPTERS_PATH, SCIENCE_CHAPTERS_PATH


def _read_json(path: Path) -> dict:
    """Read a JSON file and return its contents."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: dict):
    """Write data to a JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_profile() -> dict:
    """Get the full child profile."""
    return _read_json(CHILD_PROFILE_PATH)


def get_student_info() -> dict:
    """Get just the student info (name, class, board, school)."""
    profile = get_profile()
    return profile["student"]


def get_topics() -> list:
    """Get full topic history, sorted by date descending."""
    profile = get_profile()
    topics = profile.get("topic_history", [])
    return sorted(topics, key=lambda t: t["date"], reverse=True)


def get_topics_by_subject(subject: str) -> list:
    """Get topics filtered by subject."""
    topics = get_topics()
    return [t for t in topics if t["subject"].lower() == subject.lower()]


def get_topic_by_id(topic_id: str) -> Optional[dict]:
    """Get a specific topic by its ID."""
    topics = get_topics()
    for t in topics:
        if t["id"] == topic_id:
            return t
    return None


def get_recent_topics(n: int = 5) -> list:
    """Get the N most recent topics."""
    return get_topics()[:n]


def get_unique_topics() -> list:
    """Get unique topic names with their latest date."""
    topics = get_topics()
    seen = {}
    for t in topics:
        key = f"{t['subject']}|{t['chapter']}|{t['topic']}"
        if key not in seen:
            seen[key] = t
    return list(seen.values())


def add_topic(subject: str, chapter: str, topic: str, exercises: str, source: str = "homework_scan") -> dict:
    """Add a new topic to history. Merges if same chapter topic exists today."""
    profile = get_profile()
    today = date.today().isoformat()
    
    # Check if a topic from the same chapter was already added today
    existing = None
    for t in profile["topic_history"]:
        if (t["subject"].lower() == subject.lower() and 
            t["chapter"].lower() == chapter.lower() and 
            t["date"] == today):
            existing = t
            break
    
    if existing:
        # Merge: append subtopic info if different
        if topic.lower() not in existing["topic"].lower():
            existing["topic"] = f"{existing['topic']}, {topic}"
        if exercises and exercises not in existing.get("exercises", ""):
            existing["exercises"] = f"{existing.get('exercises', '')}, {exercises}".strip(", ")
        _write_json(CHILD_PROFILE_PATH, profile)
        _update_chapter_status(subject, chapter)
        return existing
    else:
        new_topic = {
            "id": f"t{uuid.uuid4().hex[:8]}",
            "date": today,
            "subject": subject,
            "chapter": chapter,
            "topic": topic,
            "exercises": exercises,
            "source": source
        }
        profile["topic_history"].append(new_topic)
        _write_json(CHILD_PROFILE_PATH, profile)
        _update_chapter_status(subject, chapter)
        return new_topic


def _update_chapter_status(subject: str, chapter: str):
    """Mark a chapter as in_progress or covered based on topic history."""
    if subject.lower() == "mathematics":
        chapters_path = MATH_CHAPTERS_PATH
    elif subject.lower() == "science":
        chapters_path = SCIENCE_CHAPTERS_PATH
    else:
        return
    
    chapters_data = _read_json(chapters_path)
    chapter_num = None
    try:
        chapter_num = int(chapter.split(".")[0])
    except (ValueError, IndexError):
        return
    
    for ch in chapters_data["chapters"]:
        if ch["number"] == chapter_num and ch["status"] == "not_started":
            ch["status"] = "in_progress"
            _write_json(chapters_path, chapters_data)
            break


def add_quiz_result(topic_id: str, score: int, total: int, details: list):
    """Record a quiz result."""
    profile = get_profile()
    quiz_entry = {
        "id": f"q{uuid.uuid4().hex[:8]}",
        "date": date.today().isoformat(),
        "topic_id": topic_id,
        "score": score,
        "total": total,
        "details": details
    }
    profile.setdefault("quiz_history", []).append(quiz_entry)
    _write_json(CHILD_PROFILE_PATH, profile)
    return quiz_entry


def get_chapter_progress() -> dict:
    """Get chapter completion progress for all subjects."""
    math = _read_json(MATH_CHAPTERS_PATH)
    science = _read_json(SCIENCE_CHAPTERS_PATH)
    
    def count_progress(data):
        total = data["total_chapters"]
        covered = sum(1 for ch in data["chapters"] if ch["status"] in ("covered", "in_progress"))
        return {"total": total, "covered": covered, "chapters": data["chapters"]}
    
    return {
        "Mathematics": count_progress(math),
        "Science": count_progress(science)
    }
