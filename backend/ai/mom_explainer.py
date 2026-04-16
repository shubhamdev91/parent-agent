"""Mom Explainer — Topic → short explanation with everyday analogy."""

import json
import asyncio
from backend.ai.router import call_gemini
from backend.config import SYSTEM_PROMPT


EXPLAIN_PROMPT_TEMPLATE = """You need to explain a Class 10 {subject} topic to an Indian mother who may not have studied this subject. 
She needs to understand it well enough to help her child or at least know what the child is learning.

Topic: {topic}
Chapter: {chapter}
Student's name: {student_name}
Recent exercises: {exercises}

Return JSON:
{{
  "explanation": "3-4 sentence explanation in simple English. Use an everyday analogy that a parent would relate to. End with a practical tip she can use with her child.",
  "analogy": "The specific analogy used (1 sentence)",
  "tip": "A practical thing mom can ask/do with the child to check understanding"
}}

Rules:
- Write in clear, simple English
- Use analogies from daily life: cooking, shopping, measuring, sharing, etc.
- Keep it simple — no jargon
- Include the child's name in the tip
- The explanation should make the mom feel confident, not overwhelmed
- Max 4 sentences for explanation
"""


async def explain_topic(subject: str, chapter: str, topic: str, 
                        exercises: str = "", student_name: str = "Ridham") -> dict:
    """
    Generate a mom-friendly explanation of a topic.
    Includes retry logic for rate limits.
    
    Returns:
        dict with explanation, analogy, tip
    """
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            prompt = EXPLAIN_PROMPT_TEMPLATE.format(
                subject=subject,
                chapter=chapter,
                topic=topic,
                exercises=exercises,
                student_name=student_name
            )
            
            response_text = await call_gemini(
                prompt=prompt,
                system_instruction=SYSTEM_PROMPT
            )
            
            result = json.loads(response_text)
            result.setdefault("explanation", f"Could not generate explanation for {topic}.")
            result.setdefault("analogy", "")
            result.setdefault("tip", f"Ask {student_name} what they learned about this topic.")
            
            return result
            
        except Exception as e:
            error_str = str(e)
            if ("429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower()):
                if attempt < max_retries - 1:
                    wait = (attempt + 1) * 10
                    print(f"[AI] Rate limited on explanation, waiting {wait}s (attempt {attempt+1}/{max_retries})")
                    await asyncio.sleep(wait)
                    continue
            
            print(f"[AI] Explanation error: {error_str}")
            return {
                "explanation": "Could not generate explanation right now. Please try again in a moment.",
                "analogy": "",
                "tip": f"Ask {student_name} to explain the topic to you in their own words — that's a great way to check understanding!"
            }
    
    return {
        "explanation": "Explanation service is temporarily busy. Please try again shortly.",
        "analogy": "",
        "tip": f"Ask {student_name} to explain what they learned today."
    }
