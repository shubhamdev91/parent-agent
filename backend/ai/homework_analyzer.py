"""Homework Analyzer — Image → structured topic data with NCERT chapter mapping."""

import json
import asyncio
from backend.ai.router import call_gemini
from backend.config import SYSTEM_PROMPT


HOMEWORK_PROMPT = """Analyze this homework/classwork image from an Indian CBSE Class 10 student's notebook or textbook.

Extract the following information and return as JSON:
{
  "subject": "Mathematics" or "Science",
  "chapter_number": integer (1-14 for Math, 1-13 for Science),
  "chapter": "Full chapter name from NCERT (e.g., '2. Polynomials')",
  "topic": "Broad topic name — group related subtopics together (e.g., 'Polynomials - Zeroes and Factorization' NOT separate entries for 'Finding Zeroes', 'Factorization', etc.)",
  "exercises": "Brief description of exercises visible (e.g., 'Ex 2.2 - x²-2x-8, 4s²-4s+1')",
  "confidence": "high" or "medium" or "low",
  "board": "CBSE" or "ICSE" or "unknown"
}

NCERT Class 10 Mathematics Chapters:
1. Real Numbers, 2. Polynomials, 3. Pair of Linear Equations in Two Variables, 
4. Quadratic Equations, 5. Arithmetic Progressions, 6. Triangles, 
7. Coordinate Geometry, 8. Introduction to Trigonometry, 
9. Some Applications of Trigonometry, 10. Circles, 11. Areas Related to Circles,
12. Surface Areas and Volumes, 13. Statistics, 14. Probability

NCERT Class 10 Science Chapters:
1. Chemical Reactions and Equations, 2. Acids Bases and Salts, 
3. Metals and Non-metals, 4. Carbon and its Compounds, 5. Life Processes,
6. Control and Coordination, 7. How do Organisms Reproduce, 8. Heredity,
9. Light - Reflection and Refraction, 10. The Human Eye and the Colourful World,
11. Electricity, 12. Magnetic Effects of Electric Current, 
13. Our Environment

IMPORTANT Rules for topic naming:
- Map to the correct NCERT chapter from the lists above
- Use BROAD topic names that group related concepts (e.g., "Polynomials - Zeroes and Factorization" not "Finding Zeroes of Quadratic Polynomial")
- If multiple subtopics from the same chapter are visible, combine them into one topic
- The topic should be recognizable as a chapter section, not a single exercise type

If you cannot identify the content clearly, still make your best guess and set confidence to "low".
"""


async def analyze_homework(image_bytes: bytes) -> dict:
    """
    Analyze a homework photo and extract topic information.
    Maps to NCERT chapters intelligently.
    
    Args:
        image_bytes: Raw bytes of the homework image
        
    Returns:
        dict with subject, chapter, chapter_number, topic, exercises, confidence, board
    """
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            response_text = await call_gemini(
                prompt=HOMEWORK_PROMPT,
                system_instruction=SYSTEM_PROMPT,
                image_bytes=image_bytes
            )
            
            result = json.loads(response_text)
            
            # Ensure all required fields exist
            required_fields = ["subject", "chapter", "topic", "exercises", "confidence"]
            for field in required_fields:
                if field not in result:
                    result[field] = "Unknown"
            
            # Ensure chapter_number exists
            result.setdefault("chapter_number", 0)
            
            return result
            
        except json.JSONDecodeError:
            return {
                "subject": "Unknown",
                "chapter": "Unknown", 
                "chapter_number": 0,
                "topic": "Unknown",
                "exercises": "Could not parse",
                "confidence": "low",
            }
        except Exception as e:
            error_str = str(e)
            if ("429" in error_str or "quota" in error_str.lower()) and attempt < max_retries - 1:
                print(f"[AI] Rate limited on homework analysis, retrying in 10s...")
                await asyncio.sleep(10)
                continue
            
            print(f"[AI] Homework analysis error: {error_str}")
            return {
                "subject": "Unknown",
                "chapter": "Unknown",
                "chapter_number": 0,
                "topic": "Unknown", 
                "exercises": "Error analyzing image",
                "confidence": "low",
            }
    
    return {
        "subject": "Unknown",
        "chapter": "Unknown",
        "chapter_number": 0,
        "topic": "Could not analyze",
        "exercises": "",
        "confidence": "low",
    }
