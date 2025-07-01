# /bot/database/db.py

from sqlalchemy import create_engine, select, func, and_
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import datetime

from .models import Base, User, Video, Task, AdminSettings
from ..config import DATABASE_URL, bot_settings, DEFAULT_SUB_PRICE

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    # Initialize settings in DB if they don't exist
    with get_db() as db:
        if not db.query(AdminSettings).filter_by(setting_name='subscription_mode').first():
            db.add(AdminSettings(setting_name='subscription_mode', is_enabled=False))
        if not db.query(AdminSettings).filter_by(setting_name='ai_moderation_mode').first():
            db.add(AdminSettings(setting_name='ai_moderation_mode', is_enabled=False))
        if not db.query(AdminSettings).filter_by(setting_name='subscription_price').first():
            db.add(AdminSettings(setting_name='subscription_price', value=str(DEFAULT_SUB_PRICE)))
        db.commit()


@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- User Functions ---
def get_or_create_user(user_id: int, username: str = None):
    with get_db() as db:
        user = db.query(User).filter_by(user_id=user_id).first()
        if not user:
            user = User(user_id=user_id, username=username)
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

def get_user(user_id: int):
    with get_db() as db:
        return db.query(User).filter_by(user_id=user_id).first()

def update_user_status(user_id: int, status: str):
    with get_db() as db:
        user = db.query(User).filter_by(user_id=user_id).first()
        if user:
            user.status = status
            db.commit()
        return user

def add_strike(user_id: int, count: int = 1):
    with get_db() as db:
        user = db.query(User).filter_by(user_id=user_id).first()
        if user:
            user.strikes += count
            db.commit()
        return user.strikes if user else 0

# --- Video Functions ---
def add_video(owner_id: int, title: str, thumbnail_file_id: str, link: str, length_minutes: int, instructions: str):
    with get_db() as db:
        new_video = Video(
            owner_id=owner_id,
            title=title,
            thumbnail_file_id=thumbnail_file_id,
            link=link,
            length_minutes=length_minutes,
            process_instructions=instructions
        )
        db.add(new_video)
        db.commit()
        db.refresh(new_video)
        return new_video

def count_user_videos(user_id: int):
    with get_db() as db:
        return db.query(Video).filter_by(owner_id=user_id, is_active=True).count()

def get_user_videos(user_id: int):
    with get_db() as db:
        return db.query(Video).filter_by(owner_id=user_id).all()

# --- Task Functions ---
def get_task_for_user(viewer_id: int):
    with get_db() as db:
        # Find a video this user hasn't seen yet and is not their own video
        # and the owner is active
        subquery = select(Task.video_id).where(Task.viewer_id == viewer_id)

        video = db.query(Video).join(User, Video.owner_id == User.user_id)\
            .filter(Video.owner_id != viewer_id,
                    Video.is_active == True,
                    User.status == 'active',
                    ~Video.id.in_(subquery))\
            .order_by(func.random()).first() # Get a random video

        if not video:
            return None # No tasks available

        new_task = Task(video_id=video.id, viewer_id=viewer_id)
        db.add(new_task)
        db.commit()
        db.refresh(new_task)
        return new_task

def get_task_by_id(task_id: int):
    with get_db() as db:
        return db.query(Task).filter_by(id=task_id).first()

def update_task_with_proof(task_id: int, proof_file_id: str, proof_type: str):
    with get_db() as db:
        task = db.query(Task).filter_by(id=task_id).first()
        if task:
            task.status = 'proof_submitted'
            task.proof_file_id = proof_file_id
            task.proof_type = proof_type
            db.commit()
        return task

def complete_task(task_id: int):
    with get_db() as db:
        task = db.query(Task).filter_by(id=task_id).first()
        if task and task.status == 'proof_submitted':
            task.status = 'completed'
            video = db.query(Video).filter_by(id=task.video_id).first()
            if video:
                video.views_received += 1
            db.commit()
            return True
        return False
        
def invalidate_task(task_id: int, reason: str):
     with get_db() as db:
        task = db.query(Task).filter_by(id=task_id).first()
        if task:
            task.status = 'invalid_proof'
            task.rejection_reason = reason
            db.commit()
        return task

def get_pending_proof_task_for_owner(owner_id: int):
    with get_db() as db:
        return db.query(Task).join(Video).filter(
            Video.owner_id == owner_id,
            Task.status == 'proof_submitted'
        ).first()

# --- Admin Settings Functions ---
def load_settings():
    with get_db() as db:
        settings = db.query(AdminSettings).all()
        for setting in settings:
            if setting.setting_name == 'subscription_mode':
                bot_settings.subscription_mode = setting.is_enabled
            elif setting.setting_name == 'ai_moderation_mode':
                bot_settings.ai_moderation_mode = setting.is_enabled

def update_setting(setting_name: str, is_enabled: bool):
    with get_db() as db:
        setting = db.query(AdminSettings).filter_by(setting_name=setting_name).first()
        if setting:
            setting.is_enabled = is_enabled
            db.commit()
            # Update live settings object
            if setting_name == 'subscription_mode':
                bot_settings.subscription_mode = is_enabled
            elif setting_name == 'ai_moderation_mode':
                bot_settings.ai_moderation_mode = is_enabled
