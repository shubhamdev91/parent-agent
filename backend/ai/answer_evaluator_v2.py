"""Answer Evaluator v2 — per-question CBSE marking with Gemini + OCR support."""

import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

ANSWER_EVAL_PROMPT = """You are a CBSE Class 10 exam evaluator. Evaluate strictly against CBSE marking standards.

QUESTION:
Type: {question_type} | Marks: {marks}
{question_text}

CORRECT ANSWER (CBSE standard):
{correct_answer}

STUDENT'S ANSWER:
{student_answer}

STUDENT CONTEXT:
- Previous attempts on this concept: {previous_attempts}
- Current mastery on this topic: {mastery_score}%

EVALUATE:
1. Correct, partially correct, or incorrect?
2. Marks awarded (CBSE rules: MCQ = 0 or full; VSA 2m = 0/1/2; SA 3m = 0/1/2/3; LA 5m = 0 through 5 step-wise)
3. Specific conceptual gap (if any)
4. Specific encouraging feedback (not generic)
5. Should this concept be flagged for re-practice?

Return ONLY valid JSON, no markdown:
{{
    "is_correct": bool,
    "is_partial": bool,
    "score_awarded": int,
    "feedback": "specific encouraging feedback",
    "correct_answer_display": "the correct answer formatted clearly",
    "conceptual_gap": null or "specific gap identified",
    "mom_feedback": "2-3 sentence parent-friendly explanation",
    "suggest_re_practice": bool,
    "avatar_emotion": "happy|thinking|encouraging|celebrating|concerned",
    "cbse_marking_notes": "how a CBSE examiner would mark this"
}}"""

OCR_PROMPT = """You are reading a handwritten answer from a Class 10 CBSE student.

The question was: {question_text}
Expected answer format: {question_type} ({marks} marks)

Extract the student's handwritten answer from this image.
Include mathematical notation, diagrams described, and working shown.

Return ONLY valid JSON:
{{
    "extracted_text": "the student's answer as text",
    "mathematical_expressions": ["equations or formulas"],
    "working_shown": true or false,
    "confidence": 0.0 to 1.0,
    "notes": "observations about legibility"
}}"""


def build_evaluation_prompt(question: Dict, student_answer: Dict, student_context: Dict) -> str:
    """Build the Gemini prompt for answer evaluation."""
    raw = (
        student_answer.get("raw_input") or
        student_answer.get("transcribed_text") or
        student_answer.get("ocr_text") or
        ""
    )
    return ANSWER_EVAL_PROMPT.format(
        question_type=question.get("type", "SA"),
        marks=question.get("marks", 1),
        question_text=question.get("question_text", ""),
        correct_answer=question.get("correct_answer", question.get("kid_answer", "")),
        student_answer=raw,
        previous_attempts=json.dumps(student_context.get("previous_attempts_on_concept", [])),
        mastery_score=student_context.get("mastery_score", 50)
    )


def build_ocr_prompt(question: Dict) -> str:
    """Build the Gemini prompt for OCR of handwritten answer images."""
    return OCR_PROMPT.format(
        question_text=question.get("question_text", ""),
        question_type=question.get("type", "SA"),
        marks=question.get("marks", 1)
    )


def _build_mock_evaluation(is_correct: bool, marks: int) -> Dict:
    """Build a mock evaluation dict — used for testing and as fallback on Gemini error."""
    return {
        "is_correct": is_correct,
        "is_partial": False,
        "score_awarded": marks if is_correct else 0,
        "feedback": "Great job! Keep it up!" if is_correct else "Not quite — let's review this concept.",
        "correct_answer_display": "The correct answer",
        "conceptual_gap": None if is_correct else "Review this concept",
        "mom_feedback": "Ridham answered correctly." if is_correct else "Ridham needs more practice on this.",
        "suggest_re_practice": not is_correct,
        "avatar_emotion": "celebrating" if is_correct else "encouraging",
        "cbse_marking_notes": "Full marks awarded" if is_correct else "0 marks — incorrect answer"
    }


async def evaluate_text_answer(question: Dict, student_answer: Dict, student_context: Dict) -> Dict:
    """Evaluate a text or voice (transcribed) answer using Gemini."""
    from backend.ai.router import call_gemini
    prompt = build_evaluation_prompt(question, student_answer, student_context)
    try:
        raw = await call_gemini(prompt=prompt, response_mime_type="application/json")
        result = json.loads(raw) if isinstance(raw, str) else raw
        # Ensure required fields are present
        result.setdefault("avatar_emotion", "thinking")
        result.setdefault("cbse_marking_notes", "")
        result.setdefault("conceptual_gap", None)
        return result
    except Exception as e:
        logger.warning(f"Answer evaluation failed, using fallback: {e}")
        return _build_mock_evaluation(False, question.get("marks", 1))


async def evaluate_image_answer(image_path: str, question: Dict, student_context: Dict) -> Dict:
    """OCR a handwritten answer image, then evaluate the extracted text."""
    from backend.ai.router import call_gemini
    ocr_prompt = build_ocr_prompt(question)
    extracted = ""
    confidence = 0.0
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        ocr_raw = await call_gemini(
            prompt=ocr_prompt,
            image_bytes=image_bytes,
            response_mime_type="application/json"
        )
        ocr_result = json.loads(ocr_raw) if isinstance(ocr_raw, str) else ocr_raw
        extracted = ocr_result.get("extracted_text", "")
        confidence = ocr_result.get("confidence", 0.0)
    except Exception as e:
        logger.warning(f"OCR failed for {image_path}: {e}")

    student_answer_dict = {"mode": "image", "raw_input": extracted, "ocr_text": extracted}
    result = await evaluate_text_answer(question, student_answer_dict, student_context)
    result["ocr_used"] = True
    result["ocr_confidence"] = confidence
    result["ocr_raw"] = extracted
    return result
