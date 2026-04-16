"""Configuration module — loads environment variables and defines constants."""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# --- API Keys ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Gemini Model ---
GEMINI_MODEL = "gemini-2.5-flash"

# --- Paths ---
DATA_DIR = PROJECT_ROOT / "data"
CHILD_PROFILE_PATH = DATA_DIR / "child_profile.json"
MATH_CHAPTERS_PATH = DATA_DIR / "ncert_math_chapters.json"
SCIENCE_CHAPTERS_PATH = DATA_DIR / "ncert_science_chapters.json"
SAMPLE_PHOTOS_DIR = DATA_DIR / "sample_photos"
TEMP_DIR = PROJECT_ROOT / "temp"

# Create temp dir for voice file downloads
TEMP_DIR.mkdir(exist_ok=True)

# --- Server ---
BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
WEBHOOK_MODE = os.getenv("WEBHOOK_MODE", "false").lower() == "true"
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "")

# --- TV Dashboard URL (for CORS) ---
TV_DASHBOARD_URL = os.getenv("TV_DASHBOARD_URL", "http://localhost:5173")

# --- System Prompt (shared across AI modules) ---
SYSTEM_PROMPT = """You are kramm, a co-parenting teaching assistant for Indian 
mothers with children in classes 5–10 (CBSE/ICSE).

Rules:
- Communicate in clear, simple English.
- Never give full homework answers — give the mom a teaching approach.
- When analyzing homework images, extract: subject, chapter, topic, 
  subtopic, date if visible, exercise number if visible.
- When generating quizzes, create 3-5 questions at the same difficulty 
  as the homework, with clear right/wrong evaluation criteria.
- When explaining topics to mom, use everyday analogies, keep it under 
  4 sentences, assume she may not have studied this subject.
- When evaluating student answers, be encouraging but honest. Flag 
  conceptual misunderstandings specifically.
"""

def validate_config():
    """Check that required env vars are set."""
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not GOOGLE_API_KEY:
        missing.append("GOOGLE_API_KEY")
    if missing:
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")
