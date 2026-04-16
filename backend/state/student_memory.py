"""Student memory system — 6 JSON files tracking quiz history, mastery, skills, weak areas."""

import json
import logging
import threading
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional


def _read(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def _write(path: Path, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


_EMPTY_FILES = {
    "quiz_log.json": {"quizzes": []},
    "topic_mastery.json": {"topics": []},
    "skill_profile.json": {
        "current_scores": {
            "quantitative": 50, "analytical": 50, "logical_reasoning": 50,
            "conceptual_understanding": 50, "scientific_reasoning": 50,
            "procedural_fluency": 50, "problem_solving": 50
        },
        "score_history": [],
        "skill_focus_areas": [],
        "last_update": None
    },
    "weak_areas.json": {"weak_areas": []},
    "evolution_log.json": {"snapshots": []},
    "answer_history.json": {"answers": []},
}


class StudentMemory:
    def __init__(self, data_dir: Path):
        self.mem_dir = Path(data_dir) / "student_memory"
        self.mem_dir.mkdir(exist_ok=True)
        self._lock = threading.Lock()
        self._ensure_files_exist()

    def _path(self, filename: str) -> Path:
        return self.mem_dir / filename

    def _ensure_files_exist(self):
        for filename, empty in _EMPTY_FILES.items():
            p = self._path(filename)
            if not p.exists():
                _write(p, empty)

    def log_quiz_answer(
        self,
        quiz_id: str, quiz_type: str, subject: str, chapter: int, topic: str,
        question_id: str, question_text: str, question_type: str, marks: int,
        concepts_tested: List[str], bloom_level: str, skill_tags: List[str],
        student_answer: str, correct_answer: str, is_correct: bool,
        is_partial: bool, feedback: str, conceptual_gap: Optional[str],
        answer_mode: str, time_taken_seconds: int
    ) -> None:
        with self._lock:
            ah = _read(self._path("answer_history.json"))
            ah["answers"].append({
                "answer_id": str(uuid.uuid4()),
                "quiz_id": quiz_id,
                "question_id": question_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "subject": subject,
                "chapter": chapter,
                "topic": topic,
                "question_type": question_type,
                "question_text": question_text,
                "student_answer_raw": student_answer,
                "answer_mode": answer_mode,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "is_partial": is_partial,
                "score_awarded": marks if is_correct else (marks // 2 if is_partial else 0),
                "max_marks": marks,
                "conceptual_gap": conceptual_gap,
                "concepts_tested": concepts_tested,
                "bloom_level": bloom_level,
                "skill_tags": skill_tags,
                "feedback": feedback,
                "suggest_re_practice": not is_correct,
                "ocr_used": answer_mode == "image",
                "ocr_confidence": None,
            })
            _write(self._path("answer_history.json"), ah)
            try:
                self._update_topic_tally(subject, chapter, topic, is_correct, bloom_level)
            except Exception as e:
                logging.getLogger(__name__).warning(f"Topic tally update failed: {e}")

    def _update_topic_tally(self, subject: str, chapter: int, topic: str, is_correct: bool, bloom_level: str):
        tm = _read(self._path("topic_mastery.json"))
        entry = next(
            (t for t in tm["topics"]
             if t["topic_name"] == topic and t["subject"] == subject and t["chapter"] == chapter),
            None
        )
        today = date.today().isoformat()
        bloom_order = ["remember", "understand", "apply", "analyze", "evaluate", "create"]

        if entry is None:
            entry = {
                "subject": subject, "chapter": chapter, "topic_name": topic,
                "current_mastery_score": 0, "mastery_history": [],
                "trend": "stable", "needs_revision": False,
                "questions_attempted": 0, "questions_correct": 0,
                "accuracy_percentage": 0, "last_quiz_date": today,
                "bloom_level_reached": "remember"
            }
            tm["topics"].append(entry)

        entry["questions_attempted"] += 1
        if is_correct:
            entry["questions_correct"] += 1
        entry["last_quiz_date"] = today
        entry["accuracy_percentage"] = round(
            entry["questions_correct"] / entry["questions_attempted"] * 100, 1
        )

        current_idx = bloom_order.index(entry.get("bloom_level_reached", "remember"))
        new_idx = bloom_order.index(bloom_level) if bloom_level in bloom_order else 0
        if is_correct and new_idx > current_idx:
            entry["bloom_level_reached"] = bloom_level

        new_score = round(entry["accuracy_percentage"] * 0.8)
        history = entry["mastery_history"]
        history.append({"date": today, "score": new_score})
        entry["mastery_history"] = history[-10:]

        if len(history) >= 3:
            last3 = [h["score"] for h in history[-3:]]
            if last3[0] < last3[1] < last3[2]:
                entry["trend"] = "improving"
            elif last3[0] > last3[1] > last3[2]:
                entry["trend"] = "declining"
            else:
                entry["trend"] = "stable"

        trend_factor = 1.15 if entry["trend"] == "improving" else (0.85 if entry["trend"] == "declining" else 1.0)
        entry["current_mastery_score"] = min(100, round(new_score * trend_factor))
        _write(self._path("topic_mastery.json"), tm)

    def has_student_seen_question(self, question_id: str) -> bool:
        ah = _read(self._path("answer_history.json"))
        return any(a["question_id"] == question_id for a in ah["answers"])

    def get_questions_seen_ids(self) -> List[str]:
        ah = _read(self._path("answer_history.json"))
        return list({a["question_id"] for a in ah["answers"]})

    def get_student_context_for_quiz(self, subject: str, chapter: int, topic: str) -> Dict:
        tm = _read(self._path("topic_mastery.json"))
        ah = _read(self._path("answer_history.json"))
        wa = _read(self._path("weak_areas.json"))

        entry = next(
            (t for t in tm["topics"]
             if t["topic_name"] == topic and t["subject"] == subject and t["chapter"] == chapter),
            None
        )
        mastery = entry["current_mastery_score"] if entry else 0
        bloom = entry.get("bloom_level_reached", "remember") if entry else "remember"

        recent = [
            a for a in ah["answers"]
            if a["topic"] == topic and a["subject"] == subject
        ][-5:]

        weak_concepts = [
            w["concept"] for w in wa["weak_areas"]
            if w.get("topic") == topic and w.get("subject") == subject
        ]
        strong_concepts = [
            c for a in recent if a["is_correct"]
            for c in a.get("concepts_tested", [])
            if c not in weak_concepts
        ]

        return {
            "mastery_score": mastery,
            "recent_answers": recent,
            "weak_concepts": list(set(weak_concepts)),
            "strong_concepts": list(set(strong_concepts)),
            "bloom_level_reached": bloom,
            "questions_seen_ids": self.get_questions_seen_ids(),
        }

    def get_weak_areas(self, subject: Optional[str] = None) -> List[Dict]:
        wa = _read(self._path("weak_areas.json"))
        areas = wa["weak_areas"]
        if subject:
            areas = [a for a in areas if a.get("subject") == subject]
        return sorted(areas, key=lambda x: x.get("priority", 0), reverse=True)

    def get_skill_profile(self) -> Dict:
        return _read(self._path("skill_profile.json"))

    def get_topic_mastery(self, topic: str) -> Optional[Dict]:
        tm = _read(self._path("topic_mastery.json"))
        return next((t for t in tm["topics"] if t["topic_name"] == topic), None)

    def get_revision_recommendations(self, n: int = 5) -> List[Dict]:
        areas = self.get_weak_areas()
        return areas[:n]

    def flag_weak_areas(self, weak_areas_flagged: List[Dict]) -> None:
        with self._lock:
            wa = _read(self._path("weak_areas.json"))
            for flag in weak_areas_flagged:
                existing = next(
                    (w for w in wa["weak_areas"] if w["concept"] == flag["concept"]),
                    None
                )
                if existing:
                    existing.update(flag)
                else:
                    wa["weak_areas"].append(flag)
            _write(self._path("weak_areas.json"), wa)

    def mark_concept_strong(self, subject: str, chapter: int, topic: str, concept: str) -> None:
        with self._lock:
            wa = _read(self._path("weak_areas.json"))
            wa["weak_areas"] = [
                w for w in wa["weak_areas"]
                if not (w["concept"] == concept and w.get("topic") == topic and w.get("subject") == subject)
            ]
            _write(self._path("weak_areas.json"), wa)

    def update_skill_scores(self, skill_updates: Dict) -> None:
        with self._lock:
            sp = _read(self._path("skill_profile.json"))
            for skill, update in skill_updates.items():
                if skill in sp["current_scores"]:
                    sp["current_scores"][skill] = max(0, min(100, update.get("new_score", sp["current_scores"][skill])))
            sp["score_history"].append({
                "date": date.today().isoformat(),
                "scores": dict(sp["current_scores"])
            })
            sp["last_update"] = datetime.utcnow().isoformat() + "Z"
            _write(self._path("skill_profile.json"), sp)

    def update_topic_mastery(self, update: Dict) -> None:
        with self._lock:
            tm = _read(self._path("topic_mastery.json"))
            topic_name = update.get("topic")
            entry = next((t for t in tm["topics"] if t["topic_name"] == topic_name), None)
            if entry:
                entry["current_mastery_score"] = update.get("new_mastery", entry["current_mastery_score"])
                entry["trend"] = update.get("trend", entry["trend"])
                entry["bloom_level_reached"] = update.get("bloom_level_reached", entry["bloom_level_reached"])
                _write(self._path("topic_mastery.json"), tm)

    def log_evolution_note(self, quiz_id: str, note: str) -> None:
        with self._lock:
            el = _read(self._path("evolution_log.json"))
            el["snapshots"].append({
                "quiz_id": quiz_id,
                "date": date.today().isoformat(),
                "note": note
            })
            _write(self._path("evolution_log.json"), el)
