# /bot/keyboards/reply.py

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

# --- Main Menu Keyboard ---
main_menu_keyboard = ReplyKeyboardMarkup(
    [
        ["➕ Add Video", "📝 My Videos"],
        ["▶️ Get Next Task"],
        ["📊 My Stats", "⏸️ Pause Tasks"],
    ],
    resize_keyboard=True
)

# --- Inline Keyboards ---
def agree_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ I Agree & Understand the Rules", callback_data="agree_rules")]])

def proof_review_keyboard(task_id: int):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Valid Proof", callback_data=f"proof_valid_{task_id}"),
            InlineKeyboardButton("❌ Invalid Proof", callback_data=f"proof_invalid_{task_id}")
        ]
    ])

# --- Admin Keyboards ---
admin_panel_keyboard = ReplyKeyboardMarkup(
    [
        ["📊 Stats", "👥 View Users"],
        ["📢 Broadcast Message"],
        ["⚙️ Settings", "↩️ Exit Admin"],
    ],
    resize_keyboard=True
)

def admin_settings_keyboard(sub_mode: bool, ai_mode: bool):
    sub_text = "✅ Subscription ON" if sub_mode else "❌ Subscription OFF"
    ai_text = "🤖 AI Moderation ON" if ai_mode else "🤖 AI Moderation OFF"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(sub_text, callback_data="toggle_sub_mode")],
        [InlineKeyboardButton(ai_text, callback_data="toggle_ai_mode")]
    ])
