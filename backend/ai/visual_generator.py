"""Visual Generator — Topic → self-contained HTML/SVG for TV display."""

import json
from backend.ai.router import call_gemini
from backend.config import SYSTEM_PROMPT


import urllib.parse

VISUAL_PROMPT_TEMPLATE = """You are an expert prompt engineer for an AI image generator.
Create a highly detailed, descriptive prompt to generate an educational illustration explaining this Class 10 {subject} topic.

Topic: {topic}
Chapter: {chapter}
Context: {exercises}

Return JSON:
{{
  "image_prompt": "Detailed description of the image to generate. Specify that it should be an educational diagram, illustration, or visual metaphor.",
  "title": "Title for the visual"
}}
"""

async def generate_visual(subject: str, chapter: str, topic: str, exercises: str = "") -> dict:
    """
    Generate an AI image using Pollinations AI based on a Gemini-crafted prompt.
    """
    try:
        prompt = VISUAL_PROMPT_TEMPLATE.format(
            subject=subject,
            chapter=chapter,
            topic=topic,
            exercises=exercises
        )
        
        response_text = await call_gemini(
            prompt=prompt,
            system_instruction=SYSTEM_PROMPT
        )
        
        result = json.loads(response_text)
        image_prompt = result.get("image_prompt", f"Educational illustration for {topic}")
        title = result.get("title", topic)
        
        encoded_prompt = urllib.parse.quote(image_prompt)
        
        html_content = f'''
            <div style="width:100%; height:100%; display:flex; flex-direction:column; align-items:center; justify-content:center; padding: 20px; box-sizing: border-box;">
                <h2 style="color:white; margin-bottom:20px; font-family:sans-serif; text-align:center; text-shadow: 0 2px 4px rgba(0,0,0,0.5);">{title}</h2>
                <img src="https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&nologo=true" style="max-height:80%; max-width:100%; object-fit:contain; border-radius:12px; box-shadow:0 10px 30px rgba(0,0,0,0.5);" />
            </div>
        '''
        
        return {
            "html_content": html_content,
            "title": title
        }
        
    except Exception as e:
        return {
            "html_content": f"""
                <div style="color:white; font-size:24px; padding:40px; text-align:center; font-family:sans-serif;">
                    <h2 style="color:#8b5cf6;">{topic}</h2>
                    <p style="color:#94a3b8;">Visual generation error.</p>
                    <p style="color:#64748b; font-size:16px;">{str(e)}</p>
                </div>
            """,
            "title": topic
        }
