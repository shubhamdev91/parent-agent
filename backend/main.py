"""Main entry point — FastAPI app with Telegram bot + Socket.IO server."""

import sys
import asyncio
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
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

