"""Telegram bot handlers — all command, photo, voice, text, and callback handlers."""

import asyncio
from telegram import Update
from telegram.ext import ContextTypes

from backend.bot.keyboards import (
    main_menu_keyboard, topic_confirm_keyboard, post_confirm_keyboard,
    topic_selector_keyboard, quiz_display_choice_keyboard, quiz_active_keyboard,
    quiz_after_answer_keyboard, quiz_after_reveal_keyboard, quiz_endscreen_keyboard,
)
from backend.bot import messages
from backend.state.store import (
    get_profile, get_topics, get_topic_by_id, get_unique_topics,
    add_topic, add_quiz_result, get_chapter_progress
)
from backend.ai.homework_analyzer import analyze_homework
from backend.ai.quiz_generator import generate_quiz
from backend.ai.answer_evaluator import evaluate_text_answer, evaluate_voice_answer
from backend.ai.mom_explainer import explain_topic
from backend.ai.visual_generator import generate_visual
from backend.ws.server import (
    emit_topic_added, emit_timeline_refresh, emit_quiz_start,
    emit_quiz_question, emit_quiz_answer_result, emit_quiz_complete,
    emit_show_visual, emit_idle
)
from backend.config import TEMP_DIR


# --- In-memory session state (per chat) ---
_sessions = {}


def _get_session(chat_id: int) -> dict:
    """Get or create session state for a chat."""
    if chat_id not in _sessions:
        _sessions[chat_id] = {
            "pending_topic": None,
            "active_quiz": None,
            "quiz_on_tv": False,
            "awaiting_answer": True,  # Whether we're waiting for student answer
        }
    return _sessions[chat_id]


def _build_progress(quiz: dict) -> list:
    """Build visual progress list for the quiz."""
    progress = []
    for i in range(len(quiz["questions"])):
        if i < len(quiz["results"]):
            r = quiz["results"][i]
            if r.get("correct"):
                progress.append("correct")
            elif r.get("skipped"):
                progress.append("skipped")
            else:
                progress.append("wrong")
        elif i == quiz["current_index"]:
            progress.append("current")
        else:
            progress.append("pending")
    return progress


# ============================================================
# COMMAND HANDLERS
# ============================================================

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command — welcome message + main menu."""
    profile = get_profile()
    student_name = profile["student"]["name"].split()[0]
    
    welcome = messages.WELCOME_MESSAGE.format(student_name=student_name)
    await update.message.reply_text(
        welcome,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )


# ============================================================
# PHOTO HANDLER — Homework Upload
# ============================================================

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages — analyze homework image."""
    chat_id = update.effective_chat.id
    session = _get_session(chat_id)
    
    status_msg = await update.message.reply_text(messages.ANALYZING_PHOTO)
    
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    photo_bytes = await file.download_as_bytearray()
    
    result = await analyze_homework(bytes(photo_bytes))
    session["pending_topic"] = result
    
    confirm_text = messages.topic_confirmed_message(
        subject=result.get("subject", "Unknown"),
        chapter=result.get("chapter", "Unknown"),
        topic=result.get("topic", "Unknown"),
        exercises=result.get("exercises", "")
    )
    
    await status_msg.edit_text(
        confirm_text,
        parse_mode="Markdown",
        reply_markup=topic_confirm_keyboard()
    )


# ============================================================
# VOICE HANDLER — Quiz answers via voice
# ============================================================

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages — used for quiz answers."""
    chat_id = update.effective_chat.id
    session = _get_session(chat_id)
    
    quiz = session.get("active_quiz")
    if not quiz:
        await update.message.reply_text(
            "🎤 Voice message received! No quiz is active right now. Start a quiz first!",
            reply_markup=main_menu_keyboard()
        )
        return
    
    if not session.get("awaiting_answer", True):
        await update.message.reply_text("Press 'Next Question' to continue the quiz.")
        return
    
    status_msg = await update.message.reply_text(messages.VOICE_RECEIVED)
    
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    voice_bytes = await file.download_as_bytearray()
    
    current_q = quiz["questions"][quiz["current_index"]]
    
    result = await evaluate_voice_answer(
        question=current_q["question"],
        correct_answer=current_q.get("kid_answer", current_q.get("answer", "")),
        audio_bytes=bytes(voice_bytes),
        audio_mime="audio/ogg"
    )
    
    # Check if evaluation actually worked
    if "Could not" in result.get("feedback", "") or "temporarily" in result.get("feedback", ""):
        # Evaluation failed — don't advance, let student retry
        await status_msg.edit_text(
            "🎤 Could not process voice answer right now. Please try again or type your answer instead.",
            reply_markup=quiz_active_keyboard(quiz["current_index"] + 1)
        )
        return
    
    await _process_quiz_answer(update, context, session, quiz, current_q, result, status_msg)


# ============================================================
# TEXT MESSAGE HANDLER — Quiz answers via text
# ============================================================

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages — used for quiz answers during active quiz."""
    chat_id = update.effective_chat.id
    session = _get_session(chat_id)
    
    quiz = session.get("active_quiz")
    if not quiz:
        await update.message.reply_text(
            "Choose an option from below! 👇",
            reply_markup=main_menu_keyboard()
        )
        return
    
    if not session.get("awaiting_answer", True):
        await update.message.reply_text("Press 'Next Question' to continue the quiz.")
        return
    
    student_answer = update.message.text
    current_q = quiz["questions"][quiz["current_index"]]
    
    result = await evaluate_text_answer(
        question=current_q["question"],
        correct_answer=current_q.get("kid_answer", current_q.get("answer", "")),
        student_answer=student_answer
    )
    
    # Check if evaluation failed  
    if "Could not" in result.get("feedback", "") or "temporarily" in result.get("feedback", ""):
        await update.message.reply_text(
            "⚠️ Could not evaluate right now. Please try your answer again.",
            reply_markup=quiz_active_keyboard(quiz["current_index"] + 1)
        )
        return
    
    await _process_quiz_answer(update, context, session, quiz, current_q, result)


# ============================================================
# CALLBACK HANDLER — Inline keyboard buttons
# ============================================================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all inline keyboard callback queries."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    chat_id = update.effective_chat.id
    session = _get_session(chat_id)
    
    # --- Main Menu ---
    if data == "menu_main":
        profile = get_profile()
        student_name = profile["student"]["name"].split()[0]
        await query.edit_message_text(
            messages.WELCOME_MESSAGE.format(student_name=student_name),
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
    
    elif data == "menu_homework":
        await query.edit_message_text(
            "📸 Send a homework photo! I'll analyze it for you.",
            parse_mode="Markdown"
        )
    
    # --- Topic Confirmation ---
    elif data.startswith("confirm_yes"):
        topic_data = session.get("pending_topic")
        if topic_data:
            new_topic = add_topic(
                subject=topic_data["subject"],
                chapter=topic_data["chapter"],
                topic=topic_data["topic"],
                exercises=topic_data.get("exercises", "")
            )
            session["pending_topic"] = None
            
            await emit_topic_added(new_topic)
            
            await query.edit_message_text(
                messages.TOPIC_SAVED,
                parse_mode="Markdown",
                reply_markup=post_confirm_keyboard(new_topic["id"])
            )
    
    elif data.startswith("confirm_no"):
        session["pending_topic"] = None
        await query.edit_message_text(
            "❌ Alright, send the photo again or tell me the topic manually!",
            reply_markup=main_menu_keyboard()
        )
    
    # --- Quiz Mode ---
    elif data == "menu_quiz":
        topics = get_unique_topics()
        if not topics:
            await query.edit_message_text(
                "📝 Send a homework photo first, then you can take a quiz!",
                reply_markup=main_menu_keyboard()
            )
            return
        await query.edit_message_text(
            "📝 *Quiz Mode* — Which topic?\n\nChoose from below:",
            parse_mode="Markdown",
            reply_markup=topic_selector_keyboard(topics, action="quiz")
        )
    
    elif data.startswith("quiz_topic:"):
        topic_id = data.split(":", 1)[1]
        await _start_quiz(query, session, topic_id)
    
    elif data == "quiz_on_tv":
        session["quiz_on_tv"] = True
        quiz = session.get("active_quiz")
        if quiz:
            topic_data = quiz["topic_data"]
            await emit_quiz_start(topic_data["topic"], len(quiz["questions"]))
            
            q = quiz["questions"][0]
            progress = _build_progress(quiz)
            await emit_quiz_question(
                1, 
                q["question"], 
                topic_data["topic"],
                kid_answer=q.get("kid_answer", q.get("answer", "")),
                mom_explanation=q.get("mom_explanation", q.get("explanation", ""))
            )
            
            session["awaiting_answer"] = True
            await query.edit_message_text(
                messages.TV_QUIZ_PUSHED + "\n\n" + 
                messages.quiz_question_message(1, len(quiz["questions"]), q["question"], progress),
                parse_mode="Markdown",
                reply_markup=quiz_active_keyboard(1)
            )
    
    elif data == "quiz_on_phone":
        session["quiz_on_tv"] = False
        quiz = session.get("active_quiz")
        if quiz:
            q = quiz["questions"][0]
            progress = _build_progress(quiz)
            session["awaiting_answer"] = True
            await query.edit_message_text(
                messages.quiz_question_message(1, len(quiz["questions"]), q["question"], progress),
                parse_mode="Markdown",
                reply_markup=quiz_active_keyboard(1)
            )
    
    elif data.startswith("quiz_skip:"):
        quiz = session.get("active_quiz")
        if quiz:
            current_q = quiz["questions"][quiz["current_index"]]
            quiz["results"].append({
                "question": current_q["question"],
                "kid_answer": current_q.get("kid_answer", current_q.get("answer", "")),
                "mom_explanation": current_q.get("mom_explanation", current_q.get("explanation", "")),
                "correct": False,
                "skipped": True
            })
            quiz["current_index"] += 1
            
            if quiz["current_index"] >= len(quiz["questions"]):
                await _finish_quiz(query, session, quiz)
            else:
                session["awaiting_answer"] = True
                await _send_next_question(query, session, quiz)
    
    elif data == "quiz_stop":
        quiz = session.get("active_quiz")
        if quiz:
            try:
                await _finish_quiz(query, session, quiz)
            except Exception as e:
                print(f"[BOT] Error stopping quiz: {e}")
                session["active_quiz"] = None
                session["quiz_on_tv"] = False
                if session.get("quiz_on_tv"):
                    await emit_idle()
                try:
                    await query.edit_message_text(
                        "Quiz stopped! 🏠",
                        reply_markup=main_menu_keyboard()
                    )
                except:
                    pass
        else:
            try:
                await query.edit_message_text(
                    "No quiz active! 🏠",
                    reply_markup=main_menu_keyboard()
                )
            except:
                pass
    
    elif data.startswith("quiz_reveal:"):
        # Mom reveals answer for current question
        quiz = session.get("active_quiz")
        if quiz:
            q_idx = quiz["current_index"]
            q = quiz["questions"][q_idx]
            total = len(quiz["questions"])
            has_next = q_idx + 1 < total
            
            kid_ans = q.get("kid_answer", q.get("answer", "N/A"))
            mom_exp = q.get("mom_explanation", q.get("explanation", ""))
            
            from backend.ws.server import emit_quiz_reveal
            await emit_quiz_reveal(q_idx + 1)
                
            await query.edit_message_text(
                messages.quiz_answer_reveal(q_idx + 1, q["question"], kid_ans, mom_exp),
                parse_mode="Markdown",
                reply_markup=quiz_after_reveal_keyboard(q_idx + 1, total, has_next)
            )
    
    elif data.startswith("quiz_explain:"):
        # Show explanation after answer
        quiz = session.get("active_quiz")
        if quiz and quiz["results"]:
            last_result = quiz["results"][-1]
            q_idx = quiz["current_index"]  # Already advanced
            total = len(quiz["questions"])
            has_next = q_idx < total
            
            kid_ans = quiz["questions"][q_idx - 1].get("kid_answer", quiz["questions"][q_idx - 1].get("answer", "N/A")) if q_idx > 0 else "N/A"
            mom_exp = quiz["questions"][q_idx - 1].get("mom_explanation", quiz["questions"][q_idx - 1].get("explanation", "")) if q_idx > 0 else ""
            feedback = last_result.get("feedback", "")
            
            await query.edit_message_text(
                f"📖 *Explanation:*\n\n"
                f"✅ *Kid's Answer:* {kid_ans}\n\n"
                f"👩‍🏫 *Mom's Explanation:* {mom_exp}\n\n"
                f"💬 {feedback}",
                parse_mode="Markdown",
                reply_markup=quiz_after_reveal_keyboard(q_idx, total, has_next)
            )
    
    elif data.startswith("quiz_next:"):
        # Advance to next question
        quiz = session.get("active_quiz")
        if quiz:
            # Check if this question was skipped
            if len(quiz["results"]) == quiz["current_index"]:
                current_q = quiz["questions"][quiz["current_index"]]
                quiz["results"].append({
                    "question": current_q["question"],
                    "kid_answer": current_q.get("kid_answer", current_q.get("answer", "N/A")),
                    "mom_explanation": current_q.get("mom_explanation", current_q.get("explanation", "")),
                    "correct": False,
                    "skipped": True
                })
                quiz["current_index"] += 1
            if quiz["current_index"] < len(quiz["questions"]):
                session["awaiting_answer"] = True
                await _send_next_question(query, session, quiz)
            else:
                await _finish_quiz(query, session, quiz)
    
    elif data == "quiz_reveal_all":
        # Reveal all answers at endscreen
        quiz_results = session.get("_last_quiz_results")
        if quiz_results:
            msg = "📖 *All Answers:*\n\n"
            for i, q in enumerate(quiz_results["questions"]):
                result = quiz_results["results"][i] if i < len(quiz_results["results"]) else {}
                icon = "✅" if result.get("correct") else "⏭" if result.get("skipped") else "❌"
                msg += f"{icon} *Q{i+1}:* {q['question'][:60]}\n"
                kid_ans = q.get('kid_answer', q.get('answer', ''))[:80]
                msg += f"   Answer: _{kid_ans}_\n\n"
            
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📺 View Full Topic Visualizer", callback_data=f"visual_topic:{quiz['topic_data']['id']}")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_main")],
            ])
            await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=keyboard)
            
    elif data.startswith("quiz_visual:"):
        question_num = int(data.split(":")[1])
        quiz = session.get("active_quiz")
        if quiz:
            q = quiz["questions"][question_num - 1]
            await query.answer("🖼 Generating visual on TV...", show_alert=False)
            
            visual_data = await generate_visual(
                subject=quiz["topic_data"]["subject"],
                chapter=quiz["topic_data"]["chapter"],
                topic=quiz["topic_data"]["topic"],
                exercises=f"Generate a diagram specifically explaining this question: {q['question']}"
            )
            
            from backend.ws.server import emit_show_visual
            await emit_show_visual(topic=quiz["topic_data"]["topic"], html_content=visual_data["html_content"])
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Another Quiz", callback_data="menu_quiz")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_main")],
            ])
            await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=keyboard)
    
    elif data == "quiz_show_tv":
        quiz = session.get("active_quiz")
        if quiz:
            session["quiz_on_tv"] = True
            q = quiz["questions"][quiz["current_index"]]
            await emit_quiz_question(
                quiz["current_index"] + 1, 
                q["question"],
                quiz["topic_data"]["topic"],
                kid_answer=q.get("kid_answer", q.get("answer", "")),
                mom_explanation=q.get("mom_explanation", q.get("explanation", ""))
            )
            await query.answer("📺 Showing on TV!")
    
    # --- Explain Mode ---
    elif data == "menu_explain":
        topics = get_unique_topics()
        if not topics:
            await query.edit_message_text(
                "💡 Send a homework photo first, then I can explain!",
                reply_markup=main_menu_keyboard()
            )
            return
        await query.edit_message_text(
            "💡 *Explain Mode* — Which topic do you want explained?\n\nChoose below:",
            parse_mode="Markdown",
            reply_markup=topic_selector_keyboard(topics, action="explain")
        )
    
    elif data.startswith("explain_topic:"):
        from backend.state.cache import get_cached, set_cached
        topic_id = data.split(":", 1)[1]
        topic_data = get_topic_by_id(topic_id)
        if not topic_data:
            await query.edit_message_text("Topic not found!", reply_markup=main_menu_keyboard())
            return
        
        # Check cache
        cached = get_cached(topic_id, "explanation")
        if cached:
            result = cached
        else:
            await query.edit_message_text("💡 Preparing explanation... please wait...")
            
            profile = get_profile()
            student_name = profile["student"]["name"].split()[0]
            
            result = await explain_topic(
                subject=topic_data["subject"],
                chapter=topic_data["chapter"],
                topic=topic_data["topic"],
                exercises=topic_data.get("exercises", ""),
                student_name=student_name
            )
            set_cached(topic_id, "explanation", result,
                       subject=topic_data["subject"],
                       chapter=topic_data["chapter"],
                       topic=topic_data["topic"])
        
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📺 Show visual on TV", callback_data=f"visual_topic:{topic_id}")],
            [InlineKeyboardButton("📝 Take a quiz", callback_data=f"quiz_topic:{topic_id}")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_main")],
        ])
        
        await query.edit_message_text(
            messages.explanation_message(result["explanation"], result["tip"]),
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    
    # --- TV Visual ---
    elif data.startswith("visual_topic:"):
        from backend.state.cache import get_cached, set_cached
        topic_id = data.split(":", 1)[1]
        topic_data = get_topic_by_id(topic_id)
        if not topic_data:
            await query.edit_message_text("Topic not found!", reply_markup=main_menu_keyboard())
            return
        
        # Check cache
        cached = get_cached(topic_id, "visual")
        if cached:
            result = cached
        else:
            await query.edit_message_text("📺 Creating visual for TV...")
            
            result = await generate_visual(
                subject=topic_data["subject"],
                chapter=topic_data["chapter"],
                topic=topic_data["topic"],
                exercises=topic_data.get("exercises", "")
            )
            set_cached(topic_id, "visual", result,
                       subject=topic_data["subject"],
                       chapter=topic_data["chapter"],
                       topic=topic_data["topic"])
        
        await emit_show_visual(topic_data["topic"], result["html_content"])
        
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Take a quiz", callback_data=f"quiz_topic:{topic_id}")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_main")],
        ])
        
        await query.edit_message_text(
            messages.TV_VISUAL_PUSHED,
            reply_markup=keyboard
        )
    
    # --- TV Timeline ---
    elif data == "menu_tv_timeline":
        topics = get_topics()
        await emit_timeline_refresh(topics)
        await query.edit_message_text(
            messages.TV_TIMELINE_PUSHED,
            reply_markup=main_menu_keyboard()
        )
    
    elif data.startswith("tv_show:"):
        topic_id = data.split(":", 1)[1]
        topics = get_topics()
        await emit_timeline_refresh(topics)
        await query.edit_message_text(
            messages.TV_TIMELINE_PUSHED,
            reply_markup=main_menu_keyboard()
        )
    
    elif data == "noop":
        await query.answer()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

async def _start_quiz(query, session, topic_id):
    """Generate quiz and show overview. Uses cache if available."""
    from backend.state.cache import get_cached, set_cached
    
    topic_data = get_topic_by_id(topic_id)
    if not topic_data:
        await query.edit_message_text("Topic not found!", reply_markup=main_menu_keyboard())
        return
    
    # Check cache first
    cached_questions = None # Force bypass to enforce new 7-question split schema
    if cached_questions:
        questions = cached_questions
        await query.edit_message_text(
            f"📝 *{topic_data['topic']}* — loading quiz...", 
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text(
            f"📝 *{topic_data['topic']}* — generating quiz...", 
            parse_mode="Markdown"
        )
        
        questions = await generate_quiz(
            subject=topic_data["subject"],
            chapter=topic_data["chapter"],
            topic=topic_data["topic"],
            exercises=topic_data.get("exercises", ""),
            count=7
        )
        
        # Cache the generated quiz
        set_cached(topic_id, "quiz", questions,
                   subject=topic_data["subject"],
                   chapter=topic_data["chapter"],
                   topic=topic_data["topic"])
    
    session["active_quiz"] = {
        "topic_data": topic_data,
        "questions": questions,
        "current_index": 0,
        "results": [],
    }
    session["quiz_on_tv"] = False
    session["awaiting_answer"] = False
    
    # Show overview with all questions listed
    await query.edit_message_text(
        messages.quiz_overview_message(
            topic_data["topic"], 
            topic_data["chapter"],
            len(questions), 
            questions
        ),
        parse_mode="Markdown",
        reply_markup=quiz_display_choice_keyboard()
    )


async def _process_quiz_answer(update, context, session, quiz, current_q, result, status_msg=None):
    """Process a quiz answer result (from text or voice)."""
    is_correct = result.get("correct", False)
    feedback = result.get("feedback", "")
    avatar = result.get("avatar", "🤔")
    correct_answer_display = result.get("correct_answer_display", current_q.get("kid_answer", current_q.get("answer", "")))
    
    # Record result
    quiz["results"].append({
        "question": current_q["question"],
        "kid_answer": current_q.get("kid_answer", current_q.get("answer", "")),
        "mom_explanation": current_q.get("mom_explanation", current_q.get("explanation", "")),
        "correct": is_correct,
        "feedback": feedback,
        "correct_answer_display": correct_answer_display,
        "skipped": False
    })
    
    # Push to TV ALWAYS so it unlocks if connected
    from backend.ws.server import emit_quiz_answer_result
    await emit_quiz_answer_result(
        correct=is_correct,
        feedback=feedback,
        avatar=avatar,
        question_number=quiz["current_index"] + 1
    )
    
    # Build feedback message — always show correct answer
    progress = _build_progress(quiz)
    progress_bar = ""
    for s in progress:
        progress_bar += {"correct": "✅", "wrong": "❌", "skipped": "⏭", "current": "❓", "pending": "⬜"}.get(s, "⬜")
    
    if is_correct:
        feedback_text = f"✅ *Correct!*\n\n{feedback}"
    else:
        feedback_text = (
            f"❌ *Incorrect*\n\n"
            f"📖 *Correct answer:* {correct_answer_display}\n\n"
            f"💬 {feedback}"
        )
    
    feedback_text = f"*Progress:* {progress_bar}\n\n{feedback_text}"
    
    # Advance index
    quiz["current_index"] += 1
    session["awaiting_answer"] = False
    
    total = len(quiz["questions"])
    has_next = quiz["current_index"] < total
    q_num = quiz["current_index"]
    
    if not has_next:
        target = status_msg or update.message
        if status_msg:
            await status_msg.edit_text(feedback_text, parse_mode="Markdown")
        else:
            await update.message.reply_text(feedback_text, parse_mode="Markdown")
        
        await asyncio.sleep(1)
        await _finish_quiz_message(update, context, session, quiz)
    else:
        if status_msg:
            await status_msg.edit_text(
                feedback_text,
                parse_mode="Markdown",
                reply_markup=quiz_after_answer_keyboard(q_num, total, has_next)
            )
        else:
            await update.message.reply_text(
                feedback_text,
                parse_mode="Markdown",
                reply_markup=quiz_after_answer_keyboard(q_num, total, has_next)
            )


async def _send_next_question(query, session, quiz):
    """Send the next quiz question with progress."""
    q = quiz["questions"][quiz["current_index"]]
    q_num = quiz["current_index"] + 1
    total = len(quiz["questions"])
    progress = _build_progress(quiz)
    
    if session.get("quiz_on_tv"):
        await emit_quiz_question(
            q_num, 
            q["question"], 
            quiz["topic_data"]["topic"],
            kid_answer=q.get("kid_answer", q.get("answer", "")),
            mom_explanation=q.get("mom_explanation", q.get("explanation", ""))
        )
    
    await query.edit_message_text(
        messages.quiz_question_message(q_num, total, q["question"], progress),
        parse_mode="Markdown",
        reply_markup=quiz_active_keyboard(q_num)
    )


async def _finish_quiz(query, session, quiz):
    """Finish quiz from a callback (skip/stop)."""
    score = sum(1 for r in quiz["results"] if r.get("correct"))
    total = len(quiz["questions"])
    
    weak_areas = [r["question"][:50] for r in quiz["results"] if not r.get("correct") and not r.get("skipped")]
    
    add_quiz_result(
        topic_id=quiz["topic_data"]["id"],
        score=score,
        total=total,
        details=quiz["results"]
    )
    
    if session.get("quiz_on_tv"):
        await emit_quiz_complete(score, total, quiz["results"], weak_areas)
    
    # Save quiz data for "reveal all" feature
    session["_last_quiz_results"] = {
        "questions": quiz["questions"],
        "results": quiz["results"],
    }
    
    session["active_quiz"] = None
    session["quiz_on_tv"] = False
    
    await query.edit_message_text(
        messages.quiz_endscreen_message(score, total, quiz["results"], weak_areas),
        parse_mode="Markdown",
        reply_markup=quiz_endscreen_keyboard()
    )


async def _finish_quiz_message(update, context, session, quiz):
    """Finish quiz from a text/voice message."""
    score = sum(1 for r in quiz["results"] if r.get("correct"))
    total = len(quiz["questions"])
    
    weak_areas = [r["question"][:50] for r in quiz["results"] if not r.get("correct") and not r.get("skipped")]
    
    add_quiz_result(
        topic_id=quiz["topic_data"]["id"],
        score=score,
        total=total,
        details=quiz["results"]
    )
    
    if session.get("quiz_on_tv"):
        await emit_quiz_complete(score, total, quiz["results"], weak_areas)
    
    # Save quiz data for "reveal all" feature
    session["_last_quiz_results"] = {
        "questions": quiz["questions"],
        "results": quiz["results"],
    }
    
    session["active_quiz"] = None
    session["quiz_on_tv"] = False
    
    msg = update.message or update.callback_query.message
    await msg.reply_text(
        messages.quiz_endscreen_message(score, total, quiz["results"], weak_areas),
        parse_mode="Markdown",
        reply_markup=quiz_endscreen_keyboard()
    )
