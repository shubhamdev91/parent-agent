"""Telegram message templates — all user-facing text in English."""


WELCOME_MESSAGE = """🎓 Welcome to *kramm*!

I'll help you track {student_name}'s studies and understand their topics.

📸 *Send Homework Photo* — I'll identify the topic
📝 *Quiz Mode* — Test {student_name}'s knowledge
💡 *Explain* — Any topic in simple language
📊 *TV Dashboard* — Show progress on TV

Choose an option below! 👇"""


ANALYZING_PHOTO = "📖 Analyzing homework... please wait..."


def topic_confirmed_message(subject: str, chapter: str, topic: str, exercises: str) -> str:
    return (
        f"📖 This looks like *{subject}* homework:\n\n"
        f"📚 Chapter: *{chapter}*\n"
        f"📌 Topic: *{topic}*\n"
        f"✏️ Exercises: {exercises}\n\n"
        f"Is this correct?"
    )


TOPIC_SAVED = "✅ Saved to the timeline! What would you like to do next?"


def quiz_overview_message(topic: str, chapter: str, count: int, questions: list) -> str:
    """Show quiz overview with all questions listed."""
    msg = (
        f"📝 *Quiz Ready — {topic}*\n"
        f"📚 {chapter}\n"
        f"📊 {count} questions\n\n"
    )
    for i, q in enumerate(questions):
        difficulty = q.get("difficulty", "medium")
        diff_icon = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(difficulty, "🟡")
        msg += f"  {diff_icon} Q{i+1}: {difficulty.capitalize()}\n"
    
    msg += "\nWhere should the quiz be displayed?"
    return msg


def quiz_question_message(q_num: int, total: int, question: str, progress: list) -> str:
    """Quiz question with visual progress bar."""
    # Build progress bar: ✅✅❌⬜⬜
    bar = ""
    for i, status in enumerate(progress):
        if status == "correct":
            bar += "✅"
        elif status == "wrong":
            bar += "❌"
        elif status == "skipped":
            bar += "⏭"
        elif status == "current":
            bar += "❓"
        else:
            bar += "⬜"
    
    return (
        f"*Progress:* {bar}\n\n"
        f"❓ *Question {q_num}/{total}*\n\n"
        f"{question}\n\n"
        f"_Type your answer or send a voice message_ 🎤"
    )


def quiz_result_message(correct: bool, feedback: str) -> str:
    if correct:
        return f"✅ *Correct!*\n\n{feedback}"
    else:
        return f"❌ *Incorrect*\n\n{feedback}"


def quiz_answer_reveal(q_num: int, question: str, kid_answer: str, mom_explanation: str) -> str:
    return (
        f"📖 *Answer for Q{q_num}:*\n\n"
        f"❓ {question}\n\n"
        f"✅ *Kid's Answer:* {kid_answer}\n\n"
        f"👩‍🏫 *Mom's Explanation:* {mom_explanation}"
    )


def quiz_endscreen_message(score: int, total: int, results: list, weak_areas: list) -> str:
    """End screen with per-question breakdown."""
    pct = int((score / total) * 100) if total > 0 else 0
    emoji = "🎉" if pct >= 80 else "💪" if pct >= 50 else "📚"
    
    msg = f"{emoji} *Quiz Complete!*\n\n"
    msg += f"🏆 Score: *{score}/{total}* ({pct}%)\n\n"
    
    # Per-question breakdown
    msg += "*Question Breakdown:*\n"
    for i, r in enumerate(results):
        if r.get("correct"):
            msg += f"  ✅ Q{i+1}"
        elif r.get("skipped"):
            msg += f"  ⏭ Q{i+1} (skipped)"
        else:
            msg += f"  ❌ Q{i+1}"
        msg += "\n"
    
    msg += "\n"
    
    if score == total:
        msg += "🌟 Perfect score! Excellent work!"
    elif pct >= 80:
        msg += "👏 Great job! Almost perfect!"
    elif pct >= 50:
        msg += "Good effort! A bit more practice will help."
    else:
        msg += "Keep practicing, improvement comes with effort! 💪"
    
    if weak_areas:
        msg += "\n\n📌 *Focus on these:*\n"
        for area in weak_areas:
            msg += f"  • {area}\n"
    
    return msg


def explanation_message(explanation: str, tip: str) -> str:
    return (
        f"💡 *Explanation:*\n\n"
        f"{explanation}\n\n"
        f"💭 *Tip:* {tip}"
    )


VOICE_RECEIVED = "🎤 Voice message received! Analyzing..."
VOICE_FAILED = "🎤 Could not process voice. Please type your answer instead."

TV_TIMELINE_PUSHED = "📊 Timeline updated on TV! Check it out!"
TV_VISUAL_PUSHED = "📺 Visual diagram is now showing on TV!"
TV_QUIZ_PUSHED = "📺 Quiz is showing on TV! Questions will appear there."

ERROR_MESSAGE = "⚠️ Something went wrong. Please try again."
PHOTO_NEEDED = "📸 Send a homework photo first, then I can analyze it!"
