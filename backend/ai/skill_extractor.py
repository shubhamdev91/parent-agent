"""Skill Extractor — runs post-quiz to update 7 cognitive skills + spaced repetition."""

import json
import logging
from datetime import date, timedelta
from typing import Dict, List

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are an educational psychologist analyzing a Class 10 CBSE student's quiz performance.

QUIZ RESULTS:
{quiz_results}

STUDENT'S CURRENT SKILL PROFILE:
{current_skill_scores}

TOPIC MASTERY HISTORY:
{topic_mastery_history}

Analyze this quiz and return ONLY valid JSON (no markdown):
{{
    "skill_updates": {{
        "quantitative": {{"delta": 0, "new_score": 70}},
        "analytical": {{"delta": 0, "new_score": 65}},
        "logical_reasoning": {{"delta": 0, "new_score": 55}},
        "conceptual_understanding": {{"delta": 0, "new_score": 78}},
        "scientific_reasoning": {{"delta": 0, "new_score": 65}},
        "procedural_fluency": {{"delta": 0, "new_score": 80}},
        "problem_solving": {{"delta": 0, "new_score": 62}}
    }},
    "topic_mastery_update": {{
        "topic": "{topic}",
        "previous_mastery": 0,
        "new_mastery": 0,
        "trend": "stable",
        "concepts_mastered": [],
        "concepts_weak": [],
        "bloom_level_reached": "apply"
    }},
    "weak_areas_flagged": [
        {{
            "concept": "concept_name",
            "reason": "why it needs review",
            "priority": 5,
            "next_review_date": "{tomorrow}",
            "subject": "{subject}",
            "chapter": {chapter},
            "topic": "{topic}"
        }}
    ],
    "evolution_note": "1-2 sentence summary of student progress"
}}

Rules:
- Delta range: -5 to +5 per quiz per skill
- Only flag concepts where student answered incorrectly or partially
- next_review_date: 1 day after first failure, 3 days for repeated failures
- new_score must be clamped to 0-100
"""


def build_extraction_prompt(quiz_input: Dict, skill_profile: Dict, topic_mastery_history: Dict) -> str:
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    return EXTRACTION_PROMPT.format(
        quiz_results=json.dumps(quiz_input, indent=2)[:2000],
        current_skill_scores=json.dumps(skill_profile.get("current_scores", {})),
        topic_mastery_history=json.dumps(topic_mastery_history)[:500],
        topic=quiz_input.get("topic", ""),
        subject=quiz_input.get("subject", ""),
        chapter=quiz_input.get("chapter", 0),
        tomorrow=tomorrow
    )


def _build_mock_extraction(quiz_input: Dict, skill_profile: Dict) -> Dict:
    """Deterministic extraction for testing — no Gemini call."""
    current = skill_profile.get("current_scores", {})
    total = quiz_input.get("total_score", 0)
    max_score = quiz_input.get("max_score", 1)
    ratio = total / max_score if max_score > 0 else 0

    skill_updates = {}
    for skill, score in current.items():
        tagged = [
            q for q in quiz_input.get("questions_evaluated", [])
            if skill in q.get("skill_tags", [])
        ]
        if tagged:
            correct = sum(1 for q in tagged if q.get("is_correct"))
            skill_ratio = correct / len(tagged)
            delta = 2 if skill_ratio >= 0.7 else (-2 if skill_ratio < 0.3 else 0)
        else:
            delta = 1 if ratio >= 0.7 else (-1 if ratio < 0.3 else 0)
        new_score = max(0, min(100, score + delta))
        skill_updates[skill] = {"delta": delta, "new_score": new_score}

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    weak = []
    for q in quiz_input.get("questions_evaluated", []):
        if not q.get("is_correct") and q.get("suggest_re_practice"):
            for concept in q.get("concepts_tested", []):
                weak.append({
                    "concept": concept,
                    "reason": q.get("conceptual_gap") or "Incorrect answer",
                    "priority": 7,
                    "next_review_date": tomorrow,
                    "subject": quiz_input.get("subject", ""),
                    "chapter": quiz_input.get("chapter", 0),
                    "topic": quiz_input.get("topic", "")
                })

    return {
        "skill_updates": skill_updates,
        "topic_mastery_update": {
            "topic": quiz_input.get("topic", ""),
            "previous_mastery": 50,
            "new_mastery": round(ratio * 100),
            "trend": "improving" if ratio >= 0.7 else ("declining" if ratio < 0.3 else "stable"),
            "concepts_mastered": [
                c for q in quiz_input.get("questions_evaluated", [])
                if q.get("is_correct")
                for c in q.get("concepts_tested", [])
            ],
            "concepts_weak": list({
                c for q in quiz_input.get("questions_evaluated", [])
                if not q.get("is_correct")
                for c in q.get("concepts_tested", [])
            }),
            "bloom_level_reached": "apply"
        },
        "weak_areas_flagged": weak,
        "evolution_note": f"Scored {total}/{max_score} on {quiz_input.get('topic', '')}."
    }


async def extract_skills(
    quiz_id: str,
    quiz_type: str,
    subject: str,
    chapter: int,
    topic: str,
    questions_evaluated: List[Dict],
    current_skill_profile: Dict,
    topic_mastery_history: Dict
) -> Dict:
    """Run post-quiz skill extraction via Gemini with fallback."""
    quiz_input = {
        "quiz_id": quiz_id, "quiz_type": quiz_type, "subject": subject,
        "chapter": chapter, "topic": topic,
        "questions_evaluated": questions_evaluated,
        "total_score": sum(q.get("score_awarded", 0) for q in questions_evaluated),
        "max_score": sum(q.get("marks", 1) for q in questions_evaluated),
    }
    prompt = build_extraction_prompt(quiz_input, current_skill_profile, topic_mastery_history)
    try:
        from backend.ai.router import call_gemini
        raw = await call_gemini(prompt=prompt, response_mime_type="application/json")
        result = json.loads(raw) if isinstance(raw, str) else raw
        # Validate required keys
        if all(k in result for k in ["skill_updates", "topic_mastery_update", "weak_areas_flagged", "evolution_note"]):
            return result
    except Exception as e:
        logger.warning(f"Skill extraction Gemini call failed: {e}")
    return _build_mock_extraction(quiz_input, current_skill_profile)
