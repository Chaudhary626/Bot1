# /bot/main.py

import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from . import config
from .database import db
from .handlers import user, admin, proof
from .keyboards import reply

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

def main() -> None:
    """Start the bot."""
    # Initialize the database
    db.init_db()
    
    # Load settings from DB into memory on start
    db.load_settings()
    logger.info(f"Settings loaded: Sub mode={config.bot_settings.subscription_mode}, AI mode={config.bot_settings.ai_moderation_mode}")


    # Create the Application and pass it your bot's token.
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # --- Register all handlers ---

    # Core user commands
    application.add_handler(CommandHandler("start", user.start))
    application.add_handler(CallbackQueryHandler(user.agree_rules_callback, pattern="^agree_rules$"))

    # User menu commands
    application.add_handler(user.add_video_handler)
    application.add_handler(MessageHandler(filters.Regex('^📝 My Videos$'), user.get_my_videos))
    application.add_handler(MessageHandler(filters.Regex('^📊 My Stats$'), user.get_my_stats))
    application.add_handler(MessageHandler(filters.Regex('^(⏸️ Pause Tasks|▶️ Resume Tasks)$'), user.toggle_pause_tasks))


    # Proof and task handling
    for handler in proof.proof_handlers:
        application.add_handler(handler)

    # Admin panel
    application.add_handler(admin.broadcast_handler)
    for handler in admin.admin_handlers:
        application.add_handler(handler)
        
    logger.info("All handlers registered.")

    # Run the bot until the user presses Ctrl-C
    # For production, you might want to use webhooks.
    # Read more: https://docs.python-telegram-bot.org/en/stable/telegram.ext.application.html#telegram.ext.Application.run_webhook
    logger.info("Starting bot polling...")
    application.run_polling()


if __name__ == "__main__":
    main()
