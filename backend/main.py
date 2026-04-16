"""Main entry point — FastAPI app with Telegram bot + Socket.IO server."""

import sys
import asyncio
import uvicorn
from contextlib import asynccontextmanager
import json as _json
from pathlib import Path as _Path
from fastapi import FastAPI, HTTPException
from backend.state.student_memory import StudentMemory as _StudentMemory
from fastapi.middleware.cors import CORSMiddleware
import socketio

# Fix Windows console encoding for emoji
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Force unbuffered output so prints from async tasks show up
import builtins
_original_print = builtins.print
def _flush_print(*args, **kwargs):
    kwargs.setdefault('flush', True)
    _original_print(*args, **kwargs)
builtins.print = _flush_print

from backend.config import (
    BACKEND_HOST, BACKEND_PORT, WEBHOOK_MODE, 
    RENDER_EXTERNAL_URL, TELEGRAM_BOT_TOKEN,
    TV_DASHBOARD_URL, validate_config
)
from backend.ws.server import sio


# --- Telegram Bot Setup ---
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters
)
from backend.bot.handlers import (
    start_handler, photo_handler, voice_handler,
    text_message_handler, callback_handler,
    revision_quiz_start, quick_quiz_select, reveal_answer_callback,
)


def create_bot_app():
    """Create and configure the Telegram bot application."""
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .build()
    )
    
    # Command handlers
    app.add_handler(CommandHandler("start", start_handler))
    
    # Photo handler — homework uploads
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    
    # Voice handler — quiz answers via voice
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))
    
    # Text handler — quiz answers via text
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))
    
    # Specific callback handlers — registered before generic fallback
    app.add_handler(CallbackQueryHandler(revision_quiz_start, pattern="^revision_quiz_start$"))
    app.add_handler(CallbackQueryHandler(quick_quiz_select, pattern="^quick_quiz_select$"))
    app.add_handler(CallbackQueryHandler(reveal_answer_callback, pattern="^reveal_answer\\|"))

    # Callback handler — inline keyboard buttons (generic fallback)
    app.add_handler(CallbackQueryHandler(callback_handler))

    return app


# --- FastAPI Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start/stop the Telegram bot with the FastAPI server."""
    validate_config()
    
    bot_app = create_bot_app()
    app.state.bot_app = bot_app
    bot_started = False
    
    async def start_bot_with_retry(max_retries=5):
        nonlocal bot_started
        for attempt in range(max_retries):
            try:
                await bot_app.initialize()
                await bot_app.start()
                if WEBHOOK_MODE and RENDER_EXTERNAL_URL:
                    webhook_url = f"{RENDER_EXTERNAL_URL}/telegram-webhook"
                    await bot_app.bot.set_webhook(webhook_url)
                    print(f"Telegram bot started (webhook: {webhook_url})")
                else:
                    await bot_app.updater.start_polling(drop_pending_updates=True)
                    print("Telegram bot started (polling mode)")
                bot_started = True
                return
            except Exception as e:
                wait = (attempt + 1) * 5
                print(f"[BOT] Failed to connect to Telegram (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print(f"[BOT] Retrying in {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    print("[BOT] Could not connect to Telegram. Server running without bot.")
    
    # Start bot in background so web server starts immediately 
    bot_task = asyncio.create_task(start_bot_with_retry())
    
    yield
    
    # Cleanup
    if not bot_task.done():
        bot_task.cancel()
    
    if bot_started:
        try:
            if not WEBHOOK_MODE:
                await bot_app.updater.stop()
            await bot_app.stop()
            await bot_app.shutdown()
        except Exception:
            pass


# --- FastAPI App ---
fastapi_app = FastAPI(title="Siya", lifespan=lifespan)

# CORS
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@fastapi_app.get("/health")
async def health():
    return {"status": "ok", "service": "kramm"}


@fastapi_app.get("/api/profile")
async def get_profile():
    """API endpoint for TV dashboard to fetch initial data."""
    from backend.state.store import get_profile as _get_profile, get_chapter_progress
    profile = _get_profile()
    progress = get_chapter_progress()
    return {
        "student": profile["student"],
        "topics": profile["topic_history"],
        "progress": progress
    }


@fastapi_app.get("/api/analytics/curriculum-timeline")
async def get_curriculum_timeline():
    try:
        math_path = _Path("data/ncert_math_chapters.json")
        science_path = _Path("data/ncert_science_chapters.json")
        with open(math_path) as f:
            math_meta = _json.load(f)
        with open(science_path) as f:
            science_meta = _json.load(f)
        with open(_Path("data/child_profile.json")) as f:
            profile = _json.load(f)
        mem = _StudentMemory(_Path("data"))

        def build_subject(chapters_meta_key, subject_str):
            chapters_list = chapters_meta_key.get("chapters", [])
            result = []
            for ch in chapters_list:
                ch_num = ch.get("number", ch.get("chapter_number", 0))
                ch_name = ch.get("name", ch.get("title", ""))
                topic_history = profile.get("topic_history", [])
                quiz_history = profile.get("quiz_history", [])
                topics_covered = [
                    {"name": t.get("topic", ""), "date": t.get("date", "")}
                    for t in topic_history
                    if t.get("subject", "").lower() == subject_str.lower()
                    and str(ch_num) in str(t.get("chapter", ""))
                ]
                quizzes = [
                    {"quiz_id": q.get("id", ""), "date": q.get("date", ""), "score": q.get("score", 0)}
                    for q in quiz_history
                    if str(ch_num) in str(q.get("topic_id", ""))
                ]
                status = "tested_in_quiz" if quizzes else ("covered_in_class" if topics_covered else "not_started")
                result.append({
                    "chapter_number": ch_num,
                    "name": ch_name,
                    "status": status,
                    "topics_covered": topics_covered,
                    "quizzes": quizzes,
                    "coverage_gaps": []
                })
            return result

        return {
            "math": build_subject(math_meta, "mathematics"),
            "science": build_subject(science_meta, "science")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@fastapi_app.get("/api/analytics/skill-profile")
async def get_skill_profile_endpoint():
    try:
        mem = _StudentMemory(_Path("data"))
        skill_profile = mem.get_skill_profile()
        weak_areas = mem.get_weak_areas()
        revision_recs = mem.get_revision_recommendations(n=5)
        tm_data = _json.loads((_Path("data/student_memory/topic_mastery.json")).read_text())
        scores = skill_profile["current_scores"]
        sorted_skills = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return {
            "current_scores": scores,
            "score_history": skill_profile.get("score_history", []),
            "topic_mastery": tm_data.get("topics", []),
            "weak_areas": weak_areas,
            "revision_recommendations": revision_recs,
            "strength_summary": {
                "strong": [s for s, v in sorted_skills[:3] if v >= 65],
                "needs_work": [s for s, v in sorted_skills[-3:] if v < 65]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@fastapi_app.get("/api/analytics/quiz-detail/{quiz_id}")
async def get_quiz_detail(quiz_id: str):
    try:
        quiz_log_path = _Path("data/student_memory/quiz_log.json")
        quiz_log = _json.loads(quiz_log_path.read_text())
        quiz = next((q for q in quiz_log["quizzes"] if q["quiz_id"] == quiz_id), None)
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        return quiz
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Mount Socket.IO on FastAPI ---
# Wrap FastAPI with Socket.IO ASGI app
combined_app = socketio.ASGIApp(sio, fastapi_app)


if __name__ == "__main__":
    print("Starting kramm...")
    print(f"   Backend: http://{BACKEND_HOST}:{BACKEND_PORT}")
    print(f"   TV Dashboard: {TV_DASHBOARD_URL}")
    print(f"   Mode: {'Webhook' if WEBHOOK_MODE else 'Polling'}")
    
    uvicorn.run(
        combined_app,
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        log_level="info"
    )

