"""WebSocket server — Socket.IO event emitters for TV dashboard updates."""

import sys
import socketio

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Create async Socket.IO server with CORS for TV dashboard
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",  # Allow all origins for dev; restrict in production
    logger=False,
    engineio_logger=False
)


@sio.event
async def connect(sid, environ):
    """TV dashboard connected."""
    print(f"[WS] TV dashboard connected: {sid}")


@sio.event
async def disconnect(sid):
    """TV dashboard disconnected."""
    print(f"[WS] TV dashboard disconnected: {sid}")


async def emit_topic_added(topic_data: dict):
    """Notify TV that a new topic was added to the timeline."""
    await sio.emit("topic_added", topic_data)
    print(f"[WS] Emitted topic_added: {topic_data.get('topic', 'unknown')}")


async def emit_timeline_refresh(topics: list):
    """Send full topic history to TV for a complete refresh."""
    await sio.emit("timeline_refresh", {"topics": topics})
    print(f"[WS] Emitted timeline_refresh: {len(topics)} topics")


async def emit_quiz_start(topic: str, total_questions: int):
    """Notify TV that a quiz is starting."""
    await sio.emit("quiz_start", {
        "topic": topic,
        "totalQuestions": total_questions
    })
    print(f"[WS] Emitted quiz_start: {topic}")


async def emit_quiz_question(question_number: int, question: str, topic: str, **kwargs):
    """Send a quiz question to the TV."""
    await sio.emit("quiz_question", {
        "questionNumber": question_number,
        "question": question,
        "topic": topic,
        "kidAnswer": kwargs.get("kid_answer", ""),
        "momExplanation": kwargs.get("mom_explanation", "")
    })
    print(f"[WS] Emitted quiz_question: Q{question_number}")


async def emit_quiz_reveal(question_number: int):
    """Notify TV to unblur the answer."""
    await sio.emit("quiz_reveal", {"questionNumber": question_number})
    print(f"[WS] Emitted quiz_reveal: Q{question_number}")


async def emit_quiz_answer_result(correct: bool, feedback: str, avatar: str, question_number: int):
    """Send answer evaluation result to TV."""
    await sio.emit("quiz_answer_result", {
        "correct": correct,
        "feedback": feedback,
        "avatar": avatar,
        "questionNumber": question_number
    })
    print(f"[WS] Emitted quiz_answer_result: Q{question_number} {'correct' if correct else 'wrong'}")


async def emit_quiz_complete(score: int, total: int, breakdown: list, weak_areas: list):
    """Send quiz completion summary to TV."""
    await sio.emit("quiz_complete", {
        "score": score,
        "total": total,
        "breakdown": breakdown,
        "weakAreas": weak_areas
    })
    print(f"[WS] Emitted quiz_complete: {score}/{total}")


async def emit_show_visual(topic: str, html_content: str):
    """Send a visual explanation to display on TV."""
    await sio.emit("show_visual", {
        "topic": topic,
        "htmlContent": html_content
    })
    print(f"[WS] Emitted show_visual: {topic}")


async def emit_idle():
    """Return TV to idle state."""
    await sio.emit("idle", {})
    print("[WS] Emitted idle")
