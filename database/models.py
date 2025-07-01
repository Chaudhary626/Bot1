# /bot/database/models.py

from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime, Float
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)
    username = Column(String)
    is_subscribed = Column(Boolean, default=False)
    subscription_expiry = Column(DateTime)
    strikes = Column(Integer, default=0)
    status = Column(String, default='active')  # active, paused, locked, banned
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    videos = relationship("Video", back_populates="owner")
    tasks_to_watch = relationship("Task", foreign_keys='Task.viewer_id', back_populates="viewer")

class Video(Base):
    __tablename__ = 'videos'
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    title = Column(String, nullable=False)
    thumbnail_file_id = Column(String, nullable=False)
    link = Column(String)
    length_minutes = Column(Integer, nullable=False)
    process_instructions = Column(String, nullable=False)
    is_active = Column(Boolean, default=True) # User can pause their videos
    views_received = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="videos")
    tasks = relationship("Task", back_populates="video")

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    video_id = Column(Integer, ForeignKey('videos.id'), nullable=False)
    viewer_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    status = Column(String, default='assigned') # assigned, proof_submitted, completed, invalid_proof, expired
    proof_file_id = Column(String) # Telegram file_id of the proof video/image
    proof_type = Column(String) # 'video' or 'photo'
    rejection_reason = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.datetime.utcnow)

    video = relationship("Video", back_populates="tasks")
    viewer = relationship("User", foreign_keys=[viewer_id], back_populates="tasks_to_watch")

class AdminSettings(Base):
    __tablename__ = 'admin_settings'
    id = Column(Integer, primary_key=True)
    setting_name = Column(String, unique=True, nullable=False)
    is_enabled = Column(Boolean, default=False)
    value = Column(String) # For storing things like subscription price

