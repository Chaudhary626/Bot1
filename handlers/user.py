# /bot/handlers/user.py

from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from ..database import db
from ..keyboards import reply
from ..config import MAX_VIDEOS_PER_USER
from .middleware import check_user_status

# States for ConversationHandler
TITLE, THUMBNAIL, LINK, LENGTH, PROCESS = range(5)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = db.get_or_create_user(update.effective_user.id, update.effective_user.username)
    
    welcome_text = (
        "👋 *Welcome to the YouTube Watch-to-Watch Bot!* \n\n"
        "This bot helps you grow your channel by exchanging views with other creators. \n\n"
        "📜 *Rules & Warning:* \n"
        "1. You must watch the assigned video to get your video watched. \n"
        "2. Submitting fake proof will result in a strike. \n"
        "3. Be respectful. No adult or misleading content. \n\n"
        "Failing to follow these rules will lead to a ban. Please agree to continue."
    )
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=reply.agree_keyboard())

async def agree_rules_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = db.get_or_create_user(query.from_user.id)
    
    await query.edit_message_text("✅ Thank you! You can now use the bot.", reply_markup=None)
    await context.bot.send_message(chat_id=query.from_user.id, text="Here is your main menu:", reply_markup=reply.main_menu_keyboard)

@check_user_status
async def add_video_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if db.count_user_videos(user_id) >= MAX_VIDEOS_PER_USER:
        await update.message.reply_text(f"❌ You have reached the maximum limit of {MAX_VIDEOS_PER_USER} videos. Please remove one to add another.")
        return ConversationHandler.END
        
    await update.message.reply_text("Let's add your new video! First, please send me the *Video Title*.", parse_mode='Markdown')
    return TITLE

async def received_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['title'] = update.message.text
    await update.message.reply_text("Great! Now, please send me the video *Thumbnail* (as a photo).", parse_mode='Markdown')
    return THUMBNAIL

async def received_thumbnail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("That's not a photo. Please send a thumbnail image.")
        return THUMBNAIL
        
    context.user_data['thumbnail'] = update.message.photo[-1].file_id # Get the highest resolution
    await update.message.reply_text("Nice thumbnail! Now send the *YouTube Video Link*. (Type 'skip' if you don't have one).", parse_mode='Markdown')
    return LINK

async def received_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['link'] = update.message.text if update.message.text.lower() != 'skip' else None
    await update.message.reply_text("Got it. What is the *Video Length* in minutes? (Max: 5 min). Just send the number.", parse_mode='Markdown')
    return LENGTH

async def received_length(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        length = int(update.message.text)
        if not 1 <= length <= 5:
            await update.message.reply_text("❌ Invalid length. Please provide a number between 1 and 5.")
            return LENGTH
        context.user_data['length'] = length
        await update.message.reply_text(
            "Finally, describe the *Process* for the viewer.\n"
            "e.g., 'Search my title, watch for 3 mins, like, subscribe'.",
            parse_mode='Markdown'
        )
        return PROCESS
    except ValueError:
        await update.message.reply_text("❌ That's not a valid number. Please send the length in minutes (e.g., 3).")
        return LENGTH

async def received_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['process'] = update.message.text
    
    # Save to DB
    video_data = context.user_data
    db.add_video(
        owner_id=update.effective_user.id,
        title=video_data['title'],
        thumbnail_file_id=video_data['thumbnail'],
        link=video_data.get('link'),
        length_minutes=video_data['length'],
        instructions=video_data['process']
    )
    
    await update.message.reply_text("✅ *Video Added Successfully!* \n\nTo get views on this video, you need to complete tasks. Press '▶️ Get Next Task' from the menu.", parse_mode='Markdown')
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Video submission cancelled.", reply_markup=reply.main_menu_keyboard)
    context.user_data.clear()
    return ConversationHandler.END
    
@check_user_status
async def get_my_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    videos = db.get_user_videos(user_id)
    if not videos:
        await update.message.reply_text("You haven't added any videos yet. Use '➕ Add Video' to start.")
        return

    message = "*Your Videos:*\n\n"
    for i, video in enumerate(videos, 1):
        status = "Active" if video.is_active else "Paused"
        message += (
            f"{i}. *{video.title}* \n"
            f"   - Status: {status}\n"
            f"   - Views Received: {video.views_received}\n\n"
        )
    await update.message.reply_text(message, parse_mode='Markdown')

@check_user_status
async def get_my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = db.get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("Could not fetch your stats. Try starting the bot again with /start.")
        return
        
    stats_text = (
        f"📊 *Your Stats*\n\n"
        f"Strikes: {user.strikes}/{MAX_STRIKES}\n"
        f"Status: {user.status.capitalize()}\n"
        # Add more stats here as needed, e.g., tasks completed
    )
    await update.message.reply_text(stats_text, parse_mode='Markdown')


@check_user_status
async def toggle_pause_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    new_status = ""
    new_button_text = ""
    
    if user.status == 'active':
        new_status = 'paused'
        new_button_text = "▶️ Resume Tasks"
        await update.message.reply_text("⏸️ Your tasks have been paused. You will not receive new tasks until you resume.")
    elif user.status == 'paused':
        new_status = 'active'
        new_button_text = "⏸️ Pause Tasks"
        await update.message.reply_text("✅ Your tasks have been resumed. You will now receive new tasks.")
    else:
        await update.message.reply_text(f"Your account status is currently '{user.status}'. You cannot change it.")
        return

    db.update_user_status(user_id, new_status)
    
    # Update the keyboard
    keyboard = reply.main_menu_keyboard.keyboard
    keyboard[2][1] = new_button_text # This is a bit brittle, a better approach would be to regenerate it
    
    await update.message.reply_text("Menu updated.", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))


# Conversation handler for adding a video
add_video_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex('^➕ Add Video$'), add_video_start)],
    states={
        TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_title)],
        THUMBNAIL: [MessageHandler(filters.PHOTO, received_thumbnail)],
        LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_link)],
        LENGTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_length)],
        PROCESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_process)],
    },
    fallbacks=[CommandHandler('cancel', cancel_conversation)],
)
