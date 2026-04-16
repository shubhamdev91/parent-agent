"""Quiz Generator — Topic → quiz questions with proper answers and explanations."""

import json
import asyncio
from backend.ai.router import call_gemini
from backend.config import SYSTEM_PROMPT


QUIZ_PROMPT_TEMPLATE = """Generate an awesome, engaging quiz for an Indian CBSE student.

Subject: {subject}
Chapter: {chapter}  
Topic: {topic}
Recent exercises: {exercises}

Task: Generate up to {count} questions based on an intelligent analysis of the topic's CBSE exam weightage and syllabus scope.

Instructions:
- FIRST, mentally analyze this topic against the NCERT syllabus. If it's a small sub-topic with limited conceptual scope, do NOT force {count} questions. Give a strictly "need-based" number of questions (e.g., 2, 3, or 4). If it's a major core topic, you may generate up to {count} max questions.
- Try to make most of them MCQs (e.g. 4 or 5 questions).
- Make the rest subjective/short-answer questions.

Return the result strictly as a JSON array.

Each question MUST have:
1. `type`: Either "mcq" or "subjective".
2. `question`: The specific question. If MCQ, append the options directly in the question text or a formatted string. 
3. `kid_answer`: The exact explicit CORRECT ANSWER the student should give (the actual answer choice or the exact solution derivation).
4. `mom_explanation`: An explainer created specifically for a LAYMAN/10-year-old so that a parent who hasn't studied this recently can understand the concept effortlessly. Explain WHY the answer is correct conceptually.
5. `hint`: A helpful nudge.
6. `difficulty`: easy, medium, or hard.

Example JSON format:
[
  {{
    "type": "mcq",
    "question": "If α and β are the zeroes of the polynomial x² - 5x + 6, what is the value of α·β? \nA) 5  \nB) -5  \nC) 6  \nD) -6",
    "kid_answer": "C) 6",
    "mom_explanation": "For any polynomial like ax² + bx + c, the product of the zeroes (roots) is always c/a. Here c is 6 and a is 1. So 6/1 = 6. Conceptually, the zeroes are 2 and 3, and 2 × 3 = 6!",
    "hint": "Remember the formula for the product of zeroes: c/a",
    "difficulty": "medium"
  }},
  {{
    "type": "subjective",
    "question": "Why do herbivores generally have a longer small intestine than carnivores?",
    "kid_answer": "Herbivores eat plant material rich in cellulose. Cellulose takes longer to digest, so a longer small intestine provides more time and surface area for digestion.",
    "mom_explanation": "Plants are tough to break down because of a hard structure in their cells called cellulose. Meat is much easier to digest. Because they eat so many plants, plant-eating animals (herbivores) need a much longer digestive tube to give their bodies enough time to break down all that tough plant material.",
    "hint": "Think about what plants are made of compared to meat, and how long it takes to process.",
    "difficulty": "hard"
  }}
]
"""


async def generate_quiz(subject: str, chapter: str, topic: str, 
                        exercises: str = "", count: int = 5) -> list:
    """
    Generate quiz questions for a given topic.
    Includes retry logic for rate limit errors.
    
    Returns:
        List of question dicts with question, answer, explanation, hint, difficulty
    """
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            prompt = QUIZ_PROMPT_TEMPLATE.format(
                subject=subject,
                chapter=chapter,
                topic=topic,
                exercises=exercises,
                count=count
            )
            
            response_text = await call_gemini(
                prompt=prompt,
                system_instruction=SYSTEM_PROMPT
            )
            
            questions = json.loads(response_text)
            
            # Ensure it's a list
            if isinstance(questions, dict) and "questions" in questions:
                questions = questions["questions"]
            
            # Validate each question has proper fields
            for i, q in enumerate(questions):
                q.setdefault("topic_index", i + 1)
                q.setdefault("question", "Question not generated")
                q.setdefault("kid_answer", "Answer not available")
                q.setdefault("mom_explanation", "")
                q.setdefault("hint", "Try working through it step by step")
                q.setdefault("difficulty", "medium")
            
            return questions
            
        except json.JSONDecodeError:
            return [{
                "type": "subjective",
                "question": f"Explain the key concept of {topic} in your own words.",
                "kid_answer": "Open-ended question — evaluate based on understanding",
                "mom_explanation": f"This tests whether the student can explain {topic} clearly.",
                "hint": "Think about what makes this topic different from others",
                "difficulty": "medium"
            }]
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 15
                    print(f"[AI] Rate limited, waiting {wait_time}s before retry {attempt + 2}/{max_retries}")
                    await asyncio.sleep(wait_time)
                    continue
            
            print(f"[AI] Quiz generation error: {error_str}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(5)
                continue
            
            return [{
                "type": "subjective",
                "question": f"Explain the concept of {topic} in your own words — how does it work?",
                "kid_answer": f"Key concept of {topic} - student should demonstrate understanding",
                "mom_explanation": f"This is a fallback question because the quiz couldn't be generated. Ask the student to explain what they know about {topic}.",
                "hint": "Review your notes or textbook",
                "difficulty": "medium"
            }]
    
    return [{
        "type": "subjective",
        "question": f"Give an example related to {topic}.",
        "kid_answer": f"Any valid example related to {topic}",
        "mom_explanation": f"Check if the student can give a real example from {topic}.",
        "hint": "Look at the examples in your textbook",
        "difficulty": "easy"
    }]


ADAPTIVE_QUIZ_PROMPT = """You are an expert CBSE Class 10 educator creating personalized quiz questions.

SEED QUESTIONS (Reference — calibrate difficulty and format):
{seed_questions_formatted}

STUDENT CONTEXT:
- Topic Mastery Score: {mastery_score}%
- Weak Concepts: {weak_concepts}
- Strong Concepts: {strong_concepts}
- Highest Bloom Level Mastered: {bloom_level_reached}
- Concepts Tested Before: {recently_tested_concepts}

GENERATION REQUIREMENTS:
- Create {generation_count} NEW quiz questions on topic: {topic} ({subject}, Chapter {chapter})
- Do NOT repeat the seed questions above
- Match difficulty and style of seed questions
- Re-test weak concepts from DIFFERENT angles than seed questions
- Bloom's taxonomy: only up to {bloom_level_reached} level
- Mix MCQ and subjective questions

Return ONLY valid JSON array, no markdown:
[
  {{
    "type": "MCQ|VSA|SA|LA",
    "marks": 1,
    "question_text": "the question",
    "options": ["A", "B", "C", "D"],
    "correct_answer": "A or text answer",
    "explanation": "detailed explanation",
    "mom_explanation": "simpler explanation for parent",
    "hint": "subtle hint",
    "difficulty": "easy|medium|hard",
    "bloom_level": "remember|understand|apply|analyze|evaluate|create",
    "skill_tags": ["procedural_fluency"],
    "concepts_tested": ["concept1"],
    "adapted_for": "weak_concept_angle|strength_reinforcement|new_angle"
  }}
]"""


async def generate_adaptive_questions(
    subject: str,
    chapter: int,
    topic: str,
    quiz_type: str,
    seed_questions: list,
    student_context: dict,
    generation_count: int,
) -> list:
    """Generate new questions when banks are exhausted or language mismatch detected."""
    if generation_count <= 0:
        return []

    seed_formatted = json.dumps([
        {k: q.get(k) for k in ["question_text", "type", "difficulty", "bloom_level", "concepts"]}
        for q in seed_questions[:3]
    ], indent=2)

    recently_tested = ", ".join(
        c for a in student_context.get("recent_answers", [])[:5]
        for c in a.get("concepts_tested", [])
    ) or "none"

    prompt = ADAPTIVE_QUIZ_PROMPT.format(
        seed_questions_formatted=seed_formatted,
        mastery_score=student_context.get("mastery_score", 50),
        weak_concepts=", ".join(student_context.get("weak_concepts", [])) or "none",
        strong_concepts=", ".join(student_context.get("strong_concepts", [])) or "none",
        bloom_level_reached=student_context.get("bloom_level_reached", "apply"),
        recently_tested_concepts=recently_tested,
        generation_count=generation_count,
        topic=topic,
        subject=subject,
        chapter=chapter
    )

    for attempt in range(3):
        try:
            raw = await call_gemini(prompt, response_mime_type="application/json")
            questions = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(questions, list):
                return questions
        except Exception:
            if attempt == 2:
                return []
            await asyncio.sleep(2 ** attempt)
    return []
