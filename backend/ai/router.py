"""AI Router — routes tasks to the correct AI module with error handling."""

from google import genai
from google.genai import types
from backend.config import GOOGLE_API_KEY, GEMINI_MODEL

# Configure Gemini client
client = genai.Client(api_key=GOOGLE_API_KEY)


async def call_gemini(prompt: str, system_instruction: str = None, image_bytes: bytes = None, 
                      audio_bytes: bytes = None, audio_mime: str = "audio/ogg",
                      response_mime_type: str = "application/json") -> str:
    """
    Universal Gemini API caller.
    Supports text, image (vision), and audio inputs.
    Returns raw response text.
    """
    contents = []
    
    # Add image if provided
    if image_bytes:
        contents.append(types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"))
    
    # Add audio if provided
    if audio_bytes:
        contents.append(types.Part.from_bytes(data=audio_bytes, mime_type=audio_mime))
    
    # Add text prompt
    contents.append(prompt)
    
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type=response_mime_type,
        temperature=0.7,
    )
    
    response = await client.aio.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=config,
    )
    
    return response.text
