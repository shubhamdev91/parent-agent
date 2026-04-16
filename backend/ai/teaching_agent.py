"""Teaching Agent — generates contextual Kramm messages + avatar emotions during quiz."""

import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

TEACHING_AGENT_PROMPT = """You are Kramm, a friendly teaching assistant for Ridham, a Class 10 CBSE student.

Personality: warm, patient, encouraging. Simple language for a 15-16 year old.
NEVER condescending. Celebrate small wins. When student fails, focus on the learning opportunity.

CURRENT CONTEXT:
- Quiz topic: {topic}
- Question #{question_number} of {total_questions}
- Student mastery on this topic: {mastery_score}%
- Student's weak concepts: {weak_concepts}
- Current question: {question_text}
- Student's answer: {student_answer}
- Evaluation result: {evaluation_result}

TRIGGER: {trigger_type}

Generate a SHORT teaching message (1-3 sentences for during-quiz, 2-4 for completion).
Make it SPECIFIC to the actual question and answer. NOT generic.

Return ONLY valid JSON:
{{"message": "teaching message here", "avatar_emotion": "neutral|thinking|happy|celebrating|encouraging|concerned|teaching|hint|proud|supportive"}}
"""

_DEFAULTS = {
    "quiz_start": {"message": "Let's go! You've got this!", "avatar_emotion": "neutral"},
    "correct_answer": {"message": "Great job! That's correct!", "avatar_emotion": "happy"},
    "wrong_answer": {"message": "That's okay! Let's learn from this.", "avatar_emotion": "encouraging"},
    "partial_answer": {"message": "You're on the right track! Add a bit more detail.", "avatar_emotion": "thinking"},
    "quiz_complete_good": {"message": "Amazing work today!", "avatar_emotion": "proud"},
    "quiz_complete_poor": {"message": "Good effort! We'll keep working on this.", "avatar_emotion": "supportive"},
    "before_question": {"message": "Here comes the next question!", "avatar_emotion": "teaching"},
    "hint_requested": {"message": "Think about the key concept here.", "avatar_emotion": "hint"},
}


async def generate_teaching_message(
    trigger: str,
    topic: str,
    question_number: int,
    total_questions: int,
    mastery_score: float,
    weak_concepts: List[str],
    question_text: str = "",
    student_answer: str = "",
    evaluation_result: Optional[Dict] = None,
) -> Dict:
    """Generate a contextual teaching message for the TV dashboard."""
    prompt = TEACHING_AGENT_PROMPT.format(
        topic=topic,
        question_number=question_number,
        total_questions=total_questions,
        mastery_score=mastery_score,
        weak_concepts=", ".join(weak_concepts) or "none identified",
        question_text=question_text[:200],
        student_answer=student_answer[:200],
        evaluation_result=json.dumps(evaluation_result or {})[:300],
        trigger_type=trigger
    )
    try:
        from backend.ai.router import call_gemini
        raw = await call_gemini(prompt=prompt, response_mime_type="application/json")
        result = json.loads(raw) if isinstance(raw, str) else raw
        if "message" in result and "avatar_emotion" in result:
            return result
    except Exception as e:
        logger.warning(f"Teaching agent Gemini call failed: {e}")
    return _DEFAULTS.get(trigger, {"message": "Keep going!", "avatar_emotion": "neutral"})
