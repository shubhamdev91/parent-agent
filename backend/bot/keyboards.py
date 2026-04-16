"""Telegram inline keyboard builders."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu — shown after /start and after actions."""
    keyboard = [
        [InlineKeyboardButton("📸 Send Homework Photo", callback_data="menu_homework")],
        [InlineKeyboardButton("📝 Quiz Mode", callback_data="menu_quiz")],
        [InlineKeyboardButton("💡 Explain a Topic", callback_data="menu_explain")],
        [InlineKeyboardButton("📊 Show Timeline on TV", callback_data="menu_tv_timeline")],
    ]
    return InlineKeyboardMarkup(keyboard)


def topic_confirm_keyboard(topic_id: str = "pending") -> InlineKeyboardMarkup:
    """Confirm extracted topic from homework photo."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, correct", callback_data=f"confirm_yes:{topic_id}"),
            InlineKeyboardButton("❌ No, change it", callback_data=f"confirm_no:{topic_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def post_confirm_keyboard(topic_id: str) -> InlineKeyboardMarkup:
    """Actions after topic confirmation."""
    keyboard = [
        [InlineKeyboardButton("📝 Take a Quiz", callback_data=f"quiz_topic:{topic_id}")],
        [InlineKeyboardButton("💡 Explain This", callback_data=f"explain_topic:{topic_id}")],
        [InlineKeyboardButton("📊 Show on TV", callback_data=f"tv_show:{topic_id}")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def topic_selector_keyboard(topics: list, action: str = "quiz") -> InlineKeyboardMarkup:
    """Dynamic topic selector from history grouped by chapter."""
    keyboard = []
    
    chapters_seen = set()
    for topic in topics[:10]:
        chapter_short = topic["chapter"].split(".")[-1].strip()[:25]
        topic_short = topic["topic"][:30]
        label = f"{topic_short}"
        
        chapter_key = topic["chapter"]
        if chapter_key not in chapters_seen:
            chapters_seen.add(chapter_key)
            keyboard.append([InlineKeyboardButton(
                f"📖 {chapter_short}", 
                callback_data=f"noop"
            )])
        
        keyboard.append([InlineKeyboardButton(
            label,
            callback_data=f"{action}_topic:{topic['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="menu_main")])
    return InlineKeyboardMarkup(keyboard)


def quiz_display_choice_keyboard() -> InlineKeyboardMarkup:
    """Choose where to display quiz (shown on overview screen)."""
    keyboard = [
        [
            InlineKeyboardButton("📺 Show on TV", callback_data="quiz_on_tv"),
            InlineKeyboardButton("📱 Show Here", callback_data="quiz_on_phone"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def quiz_active_keyboard(question_num: int) -> InlineKeyboardMarkup:
    """Controls during an active quiz question."""
    keyboard = [
        [
            InlineKeyboardButton("⏭ Skip", callback_data=f"quiz_skip:{question_num}"),
            InlineKeyboardButton("🛑 Stop", callback_data="quiz_stop"),
            InlineKeyboardButton("🖼 Diagram", callback_data=f"quiz_visual:{question_num}"),
        ],
        [
            InlineKeyboardButton("👁 Reveal Answer", callback_data=f"quiz_reveal:{question_num}"),
            InlineKeyboardButton("📺 TV", callback_data="quiz_show_tv"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def quiz_after_answer_keyboard(question_num: int, total: int, has_next: bool) -> InlineKeyboardMarkup:
    """Controls shown after an answer is evaluated."""
    keyboard = []
    if has_next:
        keyboard.append([InlineKeyboardButton("➡️ Next Question", callback_data=f"quiz_next:{question_num}")])
    keyboard.append([
        InlineKeyboardButton("👁 Show Explanation", callback_data=f"quiz_explain:{question_num}"),
        InlineKeyboardButton("🖼 Open Diagram", callback_data=f"quiz_visual:{question_num}"),
    ])
    keyboard.append([
        InlineKeyboardButton("🛑 Stop Quiz", callback_data="quiz_stop"),
    ])
    return InlineKeyboardMarkup(keyboard)


def quiz_after_reveal_keyboard(question_num: int, total: int, has_next: bool) -> InlineKeyboardMarkup:
    """Controls after answer is revealed (mom chose to see it)."""
    keyboard = []
    if has_next:
        keyboard.append([InlineKeyboardButton("➡️ Next Question", callback_data=f"quiz_next:{question_num}")])
        
    keyboard.append([
        InlineKeyboardButton("🖼 Open Diagram", callback_data=f"quiz_visual:{question_num}"),
        InlineKeyboardButton("🛑 Stop Quiz", callback_data="quiz_stop")
    ])
    return InlineKeyboardMarkup(keyboard)


def quiz_endscreen_keyboard() -> InlineKeyboardMarkup:
    """Actions after quiz completion."""
    keyboard = [
        [InlineKeyboardButton("👁 Reveal All Answers", callback_data="quiz_reveal_all")],
        [InlineKeyboardButton("📝 Another Quiz", callback_data="menu_quiz")],
        [InlineKeyboardButton("💡 Explain Weak Topics", callback_data="menu_explain")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard)
