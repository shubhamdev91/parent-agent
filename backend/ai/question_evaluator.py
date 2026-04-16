"""Question Evaluator — bank-first question selection for all quiz types."""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional


class QuestionEvaluator:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.qb_dir = self.data_dir / "question_bank"
        self.nb_dir = self.data_dir / "novel_question_bank"
        self.qb_index: Dict = {}
        self.nb_index: Dict = {}
        self._load_indices()

    def _load_indices(self):
        qb_idx_path = self.qb_dir / "question_bank_index.json"
        nb_idx_path = self.nb_dir / "novel_question_bank_index.json"
        if qb_idx_path.exists():
            with open(qb_idx_path, encoding="utf-8") as f:
                self.qb_index = json.load(f)
        if nb_idx_path.exists():
            with open(nb_idx_path, encoding="utf-8") as f:
                self.nb_index = json.load(f)

    def _iter_index_chapters(self, idx: Dict):
        """Yield chapter dicts from both subject-nested and flat index formats."""
        if not idx:
            return
        # Flat format: {"chapters": [...]}
        if "chapters" in idx:
            yield from idx["chapters"]
            return
        # Subject-nested format: {"subjects": {"Mathematics": {"chapters": [...]}, ...}}
        subjects = idx.get("subjects", {})
        for subj_data in subjects.values():
            if isinstance(subj_data, dict):
                yield from subj_data.get("chapters", [])

    def _subject_matches(self, ch: Dict, subject: str) -> bool:
        """Check whether a chapter entry belongs to the requested subject."""
        subj_lower = subject.lower()
        # chapter_name key present in some formats
        ch_subj = ch.get("subject", "").lower()
        if ch_subj:
            return (
                ch_subj in subj_lower or subj_lower in ch_subj
                or ch_subj[:4] in subj_lower or subj_lower[:4] in ch_subj
            )
        # Fall back to the file path inside the chapter entry
        ch_file = ch.get("file", "").lower()
        if ch_file:
            folder = "math" if "math" in subj_lower else "science"
            return folder in ch_file
        return True  # can't determine — include by default

    def _match_keywords_to_chapters(self, topic: str, subject: str) -> List[int]:
        """Return chapter numbers whose keywords match the topic string."""
        topic_lower = topic.lower()
        matched = set()
        for idx in (self.qb_index, self.nb_index):
            for ch in self._iter_index_chapters(idx):
                if not self._subject_matches(ch, subject):
                    continue
                # Match by chapter name
                name = ch.get("chapter_name", ch.get("name", "")).lower()
                if name and (name in topic_lower or topic_lower in name):
                    matched.add(ch["chapter_number"])
                    continue
                # Match by keyword_triggers (actual field name in both indices)
                keywords = [
                    k.lower()
                    for k in ch.get("keyword_triggers", ch.get("keywords", []))
                ]
                for kw in keywords:
                    if kw and (kw in topic_lower or topic_lower in kw):
                        matched.add(ch["chapter_number"])
                        break
        return list(matched)

    def _subject_folder(self, subject: str) -> str:
        s = subject.lower()
        if "math" in s:
            return "math"
        return "science"

    def _load_bank_questions(self, subject: str, chapters: List[int]) -> List[Dict]:
        """Load all questions from given chapter numbers, both banks."""
        folder = self._subject_folder(subject)
        candidates: List[Dict] = []

        for bank_dir in (self.qb_dir, self.nb_dir):
            ch_dir = bank_dir / folder
            if not ch_dir.exists():
                continue
            for ch_num in chapters:
                # Find file matching chapter number (zero-padded or not)
                matches = list(ch_dir.glob(f"ch{ch_num:02d}_*.json"))
                if not matches:
                    matches = list(ch_dir.glob(f"ch{ch_num}_*.json"))
                if not matches:
                    continue
                path = matches[0]
                try:
                    with open(path, encoding="utf-8") as f:
                        data = json.load(f)
                except (json.JSONDecodeError, OSError):
                    continue

                if isinstance(data, list):
                    # Raw list of questions
                    candidates.extend(data)
                elif isinstance(data, dict):
                    if "questions" in data:
                        # Flat questions array at root (both NCERT and novel banks)
                        candidates.extend(data["questions"])
                    elif "topic_map" in data:
                        # Nested under topic_map (legacy / spec format)
                        for topic_data in data["topic_map"].values():
                            if isinstance(topic_data, dict):
                                candidates.extend(topic_data.get("questions", []))
        return candidates

    def _normalise_difficulty(self, diff: str) -> str:
        """Normalise difficulty to lowercase for consistent comparison."""
        return diff.lower() if diff else "medium"

    def _normalise_bloom(self, bloom: str) -> str:
        """Normalise bloom level to lowercase."""
        return bloom.lower() if bloom else "remember"

    def _score_question(
        self,
        q: Dict,
        quiz_type: str,
        student_ctx: Dict,
        topic: str,
        remaining_needs: Dict,
    ) -> float:
        mastery = student_ctx.get("mastery_score", 50)
        bloom_reached = self._normalise_bloom(student_ctx.get("bloom_level_reached", "remember"))
        seen_ids = set(student_ctx.get("questions_seen_ids", []))
        weak_concepts = set(student_ctx.get("weak_concepts", []))

        bloom_order = ["remember", "understand", "apply", "analyze", "evaluate", "create"]
        bloom_idx = {b: i for i, b in enumerate(bloom_order)}

        # 1. Topic relevance
        q_text = (
            q.get("topic", "") + " "
            + q.get("chapter_name", "") + " "
            + q.get("question_text", "")
        ).lower()
        topic_score = 100 if topic.lower() in q_text else 30

        # 2. Difficulty fit
        diff = self._normalise_difficulty(q.get("difficulty", "medium"))
        if mastery < 30:
            diff_map = {"easy": 100, "medium": 50, "hard": 0}
        elif mastery < 60:
            diff_map = {"easy": 80, "medium": 100, "hard": 50}
        else:
            diff_map = {"easy": 60, "medium": 80, "hard": 100}
        diff_score = diff_map.get(diff, 70)

        # 3. Bloom progression
        q_bloom = self._normalise_bloom(q.get("bloom_level", "remember"))
        reached_idx = bloom_idx.get(bloom_reached, 0)
        q_bloom_idx = bloom_idx.get(q_bloom, 0)
        if q_bloom_idx <= reached_idx:
            bloom_score = 100
        elif q_bloom_idx == reached_idx + 1:
            bloom_score = 50
        else:
            bloom_score = 0

        # 4. CBSE weightage (proxy via marks)
        marks = q.get("marks", 1)
        cbse_score = min(100, marks * 20)

        # 5. Novelty
        qid = q.get("id", "")
        novelty_score = 0 if qid in seen_ids else 100

        # 6. Concept coverage
        q_concepts = set(q.get("concepts", q.get("concepts_tested", [])))
        concept_score = 100 if (q_concepts & weak_concepts) else 50

        # 7. Type balance
        q_type = q.get("type", "MCQ")
        need_mcq = remaining_needs.get("mcq", 0)
        need_subj = remaining_needs.get("subjective", 0)
        if need_mcq > need_subj:
            type_score = 100 if q_type == "MCQ" else 50
        elif need_subj > need_mcq:
            type_score = 50 if q_type == "MCQ" else 100
        else:
            type_score = 75

        return (
            topic_score * 0.20
            + diff_score * 0.25
            + bloom_score * 0.15
            + cbse_score * 0.15
            + novelty_score * 0.10
            + concept_score * 0.10
            + type_score * 0.05
        ) / 100

    def evaluate_and_select(
        self,
        quiz_type: str,
        subject: str,
        chapter: int,
        topic: str,
        student_context: Dict,
        target_count: int = 7,
    ) -> Dict:
        """Main entrypoint — return quiz dict with selected questions."""
        # 1. Find relevant chapters
        chapters = self._match_keywords_to_chapters(topic, subject)
        if chapter and chapter not in chapters:
            chapters.insert(0, chapter)
        if not chapters:
            chapters = [chapter] if chapter else []

        # 2. Load candidate questions
        candidates = self._load_bank_questions(subject, chapters)
        seen_ids = set(student_context.get("questions_seen_ids", []))

        # 3. Filter and score
        remaining_needs = {"mcq": target_count // 2, "subjective": target_count // 2}
        scored = []
        for q in candidates:
            qid = q.get("id", "")
            if qid and qid in seen_ids:
                continue
            score = self._score_question(
                q, quiz_type, student_context, topic, remaining_needs
            )
            scored.append((score, q))

        # 4. Sort and select top N
        scored.sort(key=lambda x: x[0], reverse=True)
        selected = [q for _, q in scored[:target_count]]

        # 5. Flag if generation needed
        needs_generation = len(selected) < max(3, target_count // 2)
        generation_count = (
            max(0, target_count - len(selected)) if needs_generation else 0
        )

        return {
            "quiz_id": str(uuid.uuid4()),
            "questions": selected,
            "total_questions": len(selected),
            "needs_generation": needs_generation,
            "generation_count": generation_count,
            "bank_count": len(selected),
            "decision_log": {
                "total_candidates": len(candidates),
                "after_filter": len(scored),
                "selected": len(selected),
                "generation_needed": needs_generation,
            },
        }
