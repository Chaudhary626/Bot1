# /bot/handlers/middleware.py

from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from ..database import db
from ..config import bot_settings
import datetime

def check_user_status(func):
    """
    A decorator that checks the user's status (banned, subscription) before allowing a command.
    """
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = db.get_user(update.effective_user.id)
        
        if not user:
             # This should ideally not happen if /start is the entry point
            user = db.get_or_create_user(update.effective_user.id, update.effective_user.username)

        # 1. Check for ban/lock status
        if user.status in ['banned', 'locked']:
            await update.message.reply_text(f"❌ Your account is currently *{user.status}*. You cannot perform this action.", parse_mode='Markdown')
            return
            
        # 2. Check for subscription if enabled by admin
        if bot_settings.subscription_mode:
            is_subscribed = user.is_subscribed and user.subscription_expiry > datetime.datetime.utcnow()
            if not is_subscribed:
                await update.message.reply_text(
                    "🔒 This bot is currently in subscription mode. Your subscription is inactive.\n\n"
                    "Please contact an admin to subscribe and unlock the features."
                )
                return
        
        return await func(update, context, *args, **kwargs)
    return wrapped
