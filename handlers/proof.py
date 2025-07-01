# /bot/handlers/proof.py

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from ..database import db
from ..keyboards import reply
from ..config import PROOF_REVIEW_TIMEOUT_MINUTES, MAX_STRIKES
from .middleware import check_user_status

# --- TASK ASSIGNMENT ---
@check_user_status
async def get_next_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check if user has added at least one video
    if db.count_user_videos(user_id) == 0:
        await update.message.reply_text("❌ You must add at least one video before you can get a task.")
        return
        
    task = db.get_task_for_user(user_id)
    
    if not task:
        await update.message.reply_text("😴 No new tasks available at the moment. Please try again later!")
        return
        
    context.user_data['current_task_id'] = task.id
    video = task.video
    
    caption = (
        f"🔥 *New Task!* 🔥\n\n"
        f"*Title:* {video.title}\n"
        f"*Length:* {video.length_minutes} minutes\n\n"
        f"*Instructions from owner:*\n`{video.process_instructions}`\n\n"
    )
    if video.link and 'http' in video.link:
         caption += f"[Watch Video]({video.link})\n\n"
    
    caption += "After you finish, please upload a *screen recording or video* as proof."
    
    await context.bot.send_photo(
        chat_id=user_id,
        photo=video.thumbnail_file_id,
        caption=caption,
        parse_mode='Markdown'
    )

# --- PROOF SUBMISSION ---
@check_user_status
async def handle_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    task_id = context.user_data.get('current_task_id')
    if not task_id:
        await update.message.reply_text("🤔 It seems you don't have an active task. Please get a task first.")
        return
    
    proof_file_id = None
    proof_type = None
    if update.message.video:
        proof_file_id = update.message.video.file_id
        proof_type = 'video'
    elif update.message.photo:
        # Allow photo as proof too, though video is preferred
        proof_file_id = update.message.photo[-1].file_id
        proof_type = 'photo'
    else:
        await update.message.reply_text("❌ Invalid proof format. Please send a screen recording (video) or a screenshot (photo).")
        return
        
    task = db.update_task_with_proof(task_id, proof_file_id, proof_type)
    
    if not task:
        await update.message.reply_text("An error occurred. Could not find the task.")
        return
    
    await update.message.reply_text("✅ Proof submitted! The video owner will now review it. Please be patient.")
    
    # Notify the video owner
    owner_id = task.video.owner_id
    try:
        await context.bot.send_message(
            chat_id=owner_id,
            text=(
                "🔔 *New Proof Submitted for Your Video!* \n\n"
                f"A user has submitted proof for your video: *'{task.video.title}'*. \n\n"
                f"Please review it within *{PROOF_REVIEW_TIMEOUT_MINUTES} minutes* or the task will be auto-approved and the user might report you."
            ),
            parse_mode='Markdown'
        )
        if proof_type == 'video':
            await context.bot.send_video(chat_id=owner_id, video=proof_file_id, caption="Review this proof:", reply_markup=reply.proof_review_keyboard(task.id))
        else:
            await context.bot.send_photo(chat_id=owner_id, photo=proof_file_id, caption="Review this proof:", reply_markup=reply.proof_review_keyboard(task.id))
        
        # Schedule a job to auto-approve if no action is taken
        context.job_queue.run_once(
            auto_validate_proof,
            when=PROOF_REVIEW_TIMEOUT_MINUTES * 60,
            data={'task_id': task.id, 'viewer_id': task.viewer_id},
            name=f"proof_timeout_{task.id}"
        )

    except Exception as e:
        # Handle case where bot can't message owner (e.g., blocked)
        print(f"Error notifying owner {owner_id}: {e}")
        # Auto-approve the task as the owner is unreachable
        db.complete_task(task.id)
        await context.bot.send_message(chat_id=task.viewer_id, text="The video owner could not be reached. Your task has been automatically marked as complete!")

    context.user_data.pop('current_task_id', None)


# --- PROOF REVIEW ---
async def proof_review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, task_id_str = query.data.split('_', 2)[1:]
    task_id = int(task_id_str)
    
    task = db.get_task_by_id(task_id)

    if not task or task.video.owner_id != query.from_user.id:
        await query.edit_message_text("❌ This is not your task to review or it has expired.")
        return
        
    if task.status != 'proof_submitted':
        await query.edit_message_text(f"This task has already been reviewed. Final status: {task.status}")
        return

    # Remove the timeout job since the user took action
    jobs = context.job_queue.get_jobs_by_name(f"proof_timeout_{task.id}")
    for job in jobs:
        job.schedule_removal()

    viewer_id = task.viewer_id
    if action == "valid":
        db.complete_task(task_id)
        await query.edit_message_text("✅ Proof accepted! Both you and the viewer have been credited.")
        await context.bot.send_message(chat_id=viewer_id, text=f"🎉 Good news! Your proof for the video *'{task.video.title}'* has been accepted.", parse_mode='Markdown')

    elif action == "invalid":
        context.user_data[f'invalid_task_{query.from_user.id}'] = task_id
        await query.edit_message_text("Okay, you've marked the proof as invalid. Please now send a brief reason why. (e.g., 'video was not liked', 'watched for only 10 seconds')")
        # Next message from this user will be handled by 'handle_rejection_reason'
        
async def handle_rejection_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    task_id = context.user_data.get(f'invalid_task_{user_id}')
    
    if not task_id:
        return # Not in the rejection flow

    reason = update.message.text
    task = db.invalidate_task(task_id, reason)
    
    if task:
        # Add a strike to the viewer
        strikes = db.add_strike(task.viewer_id)
        
        await update.message.reply_text("Reason recorded. The user has been notified and given a strike.")
        
        # Notify the viewer
        await context.bot.send_message(
            chat_id=task.viewer_id,
            text=(
                f"❌ Your proof for *'{task.video.title}'* was rejected.\n\n"
                f"*Reason:* {reason}\n\n"
                f"You have received a strike. You now have {strikes}/{MAX_STRIKES} strikes. "
                "Please be honest in your future tasks. If you believe this is a mistake, contact an admin."
            ),
            parse_mode='Markdown'
        )
    
    context.user_data.pop(f'invalid_task_{user_id}', None)


# --- TIMEOUT JOB ---
async def auto_validate_proof(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    task_id = job_data['task_id']
    
    task = db.get_task_by_id(task_id)
    # Check if task is still pending, if so, auto-approve
    if task and task.status == 'proof_submitted':
        db.complete_task(task_id)
        owner_id = task.video.owner_id
        viewer_id = task.viewer_id
        
        # Add a strike to the owner for not responding
        db.add_strike(owner_id)

        # Notify both parties
        await context.bot.send_message(
            chat_id=viewer_id,
            text=f"Your proof for *'{task.video.title}'* has been automatically approved because the owner did not respond in time.",
            parse_mode='Markdown'
        )
        await context.bot.send_message(
            chat_id=owner_id,
            text=f"You failed to review a proof for your video *'{task.video.title}'* in time. It has been auto-approved and you have received 1 strike for being unresponsive.",
            parse_mode='Markdown'
        )

# Handlers
proof_handlers = [
    MessageHandler(filters.Regex('^▶️ Get Next Task$'), get_next_task),
    MessageHandler(filters.VIDEO | filters.PHOTO & ~filters.COMMAND, handle_proof),
    CallbackQueryHandler(proof_review_callback, pattern=r'^proof_(valid|invalid)_.+'),
    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_rejection_reason),
]
