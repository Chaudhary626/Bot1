# /bot/handlers/admin.py

from functools import wraps
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from ..config import ADMIN_IDS, bot_settings
from ..database import db
from ..keyboards import reply

# --- Decorator for Admin-only commands ---
def admin_only(func):
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ You are not authorized to use this command.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

# --- Admin Entry ---
@admin_only
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🧑‍💻 Welcome to the Admin Panel.", reply_markup=reply.admin_panel_keyboard)

@admin_only
async def exit_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Exiting Admin Panel.", reply_markup=reply.main_menu_keyboard)

# --- Settings ---
@admin_only
async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.load_settings() # Ensure live settings are loaded from DB
    await update.message.reply_text(
        "⚙️ Bot Settings",
        reply_markup=reply.admin_settings_keyboard(
            bot_settings.subscription_mode,
            bot_settings.ai_moderation_mode
        )
    )

async def toggle_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in ADMIN_IDS:
        await query.answer("❌ Unauthorized!", show_alert=True)
        return
        
    setting_to_toggle = query.data.replace("toggle_", "")
    
    if setting_to_toggle == "sub_mode":
        new_status = not bot_settings.subscription_mode
        db.update_setting('subscription_mode', new_status)
        await query.message.reply_text(f"Subscription Mode has been {'ENABLED' if new_status else 'DISABLED'}.")
    elif setting_to_toggle == "ai_mode":
        new_status = not bot_settings.ai_moderation_mode
        db.update_setting('ai_moderation_mode', new_status)
        await query.message.reply_text(f"AI Moderation has been {'ENABLED' if new_status else 'DISABLED'}.")

    # Refresh the settings keyboard
    db.load_settings()
    await query.edit_message_reply_markup(
        reply_markup=reply.admin_settings_keyboard(
            bot_settings.subscription_mode,
            bot_settings.ai_moderation_mode
        )
    )

# --- Broadcast ---
BROADCAST_MESSAGE = range(1)
@admin_only
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please send the message you want to broadcast to all users. /cancel to stop.")
    return BROADCAST_MESSAGE

async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_to_send = update.message.text
    with db.get_db() as session:
        all_users = session.query(db.User).all()
    
    sent_count = 0
    failed_count = 0
    
    await update.message.reply_text(f"Starting broadcast to {len(all_users)} users...")
    
    for user in all_users:
        try:
            await context.bot.send_message(chat_id=user.user_id, text=message_to_send)
            sent_count += 1
        except Exception as e:
            failed_count += 1
            print(f"Failed to send to {user.user_id}: {e}")
            
    await update.message.reply_text(f"📢 Broadcast complete!\n\nSent: {sent_count}\nFailed: {failed_count}")
    return -1 # End conversation

async def broadcast_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Broadcast cancelled.", reply_markup=reply.admin_panel_keyboard)
    return -1


# Admin Handlers
admin_handlers = [
    CommandHandler("admin", admin_panel),
    MessageHandler(filters.Regex('^↩️ Exit Admin$'), exit_admin_panel),
    MessageHandler(filters.Regex('^⚙️ Settings$'), show_settings),
    CallbackQueryHandler(toggle_settings_callback, pattern=r'^toggle_(sub|ai)_mode$'),
    # Add other admin command handlers here (e.g., view users, stats)
]

broadcast_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex('^📢 Broadcast Message$'), broadcast_start)],
    states={
        BROADCAST_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_send)],
    },
    fallbacks=[CommandHandler('cancel', broadcast_cancel)],
)

# You can add more handlers for viewing stats, users, managing strikes etc.
# For example:
# @admin_only
# async def view_users(update: Update, context: ContextTypes.DEFAULT_TYPE): ...
