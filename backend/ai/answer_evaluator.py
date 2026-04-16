"""Answer Evaluator — Student answer + correct answer → evaluation + feedback."""

import json
import asyncio
from backend.ai.router import call_gemini
from backend.config import SYSTEM_PROMPT


EVALUATE_TEXT_PROMPT = """You are evaluating a Class 10 CBSE student's answer to a quiz question.

Question: {question}
Correct Answer: {correct_answer}
Student's Answer: {student_answer}

Evaluate and return JSON:
{{
  "correct": true or false,
  "partial": true or false (if the approach is right but answer is wrong),
  "feedback": "2-3 sentences: First say if correct/wrong. Then explain the correct answer simply. If wrong, show what the right approach is.",
  "correct_answer_display": "The correct answer in 1-2 lines — this is shown to the student",
  "conceptual_gap": "What concept the student may be missing (or null if correct)",
  "avatar": "😊" if correct, "🤔" if partial/almost right, "💪" if wrong but good try
}}

Rules:
- Be encouraging — this is a child
- ALWAYS include the correct answer in your feedback so the student learns
- For math, check if the method is correct even if the final number is wrong
- If partially correct, acknowledge what's right before correcting
- Keep feedback under 3 sentences
"""


EVALUATE_VOICE_PROMPT = """A Class 10 CBSE student has given a voice answer to a quiz question. 
First transcribe what the student said, then evaluate their answer.

Question: {question}
Correct Answer: {correct_answer}

The audio contains the student's spoken answer in Hindi or English.

Return JSON:
{{
  "transcription": "What the student said (transcribed)",
  "correct": true or false,
  "partial": true or false,
  "feedback": "2-3 sentences: Say if correct/wrong. Explain the correct answer simply. If wrong, show the right approach.",
  "correct_answer_display": "The correct answer in 1-2 lines",
  "conceptual_gap": "Brief note on concept gap (or null if correct)",
  "avatar": "😊" if correct, "🤔" if partial, "💪" if wrong but good try
}}
"""


async def evaluate_text_answer(question: str, correct_answer: str, student_answer: str) -> dict:
    """Evaluate a text-based student answer with retry logic."""
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            prompt = EVALUATE_TEXT_PROMPT.format(
                question=question,
                correct_answer=correct_answer,
                student_answer=student_answer
            )
            
            response_text = await call_gemini(
                prompt=prompt,
                system_instruction=SYSTEM_PROMPT
            )
            
            result = json.loads(response_text)
            result.setdefault("correct", False)
            result.setdefault("partial", False)
            result.setdefault("feedback", "Answer received!")
            result.setdefault("correct_answer_display", correct_answer)
            result.setdefault("avatar", "🤔")
            
            return result
            
        except Exception as e:
            error_str = str(e)
            if ("429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower()):
                if attempt < max_retries - 1:
                    wait = (attempt + 1) * 10
                    print(f"[AI] Rate limited on text eval, waiting {wait}s (attempt {attempt+1}/{max_retries})")
                    await asyncio.sleep(wait)
                    continue
            
            print(f"[AI] Text evaluation error: {error_str}")
            return {
                "correct": False,
                "partial": False,
                "feedback": "Could not evaluate the answer right now. Please try again in a moment.",
                "correct_answer_display": correct_answer,
                "conceptual_gap": None,
                "avatar": "🤔"
            }
    
    return {
        "correct": False,
        "partial": False,
        "feedback": "Evaluation temporarily unavailable. Please try again shortly.",
        "correct_answer_display": correct_answer,
        "conceptual_gap": None,
        "avatar": "🤔"
    }


async def evaluate_voice_answer(question: str, correct_answer: str, audio_bytes: bytes,
                                 audio_mime: str = "audio/ogg") -> dict:
    """Evaluate a voice-based student answer with retry logic."""
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            prompt = EVALUATE_VOICE_PROMPT.format(
                question=question,
                correct_answer=correct_answer
            )
            
            response_text = await call_gemini(
                prompt=prompt,
                system_instruction=SYSTEM_PROMPT,
                audio_bytes=audio_bytes,
                audio_mime=audio_mime
            )
            
            result = json.loads(response_text)
            result.setdefault("transcription", "Could not transcribe")
            result.setdefault("correct", False)
            result.setdefault("partial", False) 
            result.setdefault("feedback", "Voice answer received!")
            result.setdefault("correct_answer_display", correct_answer)
            result.setdefault("avatar", "🤔")
            
            return result
            
        except Exception as e:
            error_str = str(e)
            if ("429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower()):
                if attempt < max_retries - 1:
                    wait = (attempt + 1) * 10
                    print(f"[AI] Rate limited on voice eval, waiting {wait}s (attempt {attempt+1}/{max_retries})")
                    await asyncio.sleep(wait)
                    continue
            
            print(f"[AI] Voice evaluation error: {error_str}")
            return {
                "transcription": "Could not process voice",
                "correct": False,
                "partial": False,
                "feedback": "Could not evaluate the voice answer right now. Please try again or type your answer instead.",
                "correct_answer_display": correct_answer,
                "conceptual_gap": None,
                "avatar": "🤔"
            }
    
    return {
        "transcription": "Service temporarily busy",
        "correct": False,
        "partial": False,
        "feedback": "Voice evaluation is temporarily busy. Please type your answer instead.",
        "correct_answer_display": correct_answer,
        "conceptual_gap": None,
        "avatar": "🤔"
    }
