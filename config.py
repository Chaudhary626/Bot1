# /bot/config.py

import os

# --- BOT CONFIGURATION ---
# Get your Bot Token from @BotFather on Telegram
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# --- ADMIN CONFIGURATION ---
# Your Telegram User ID (can be a list of multiple admins)
# You can get your user ID by messaging @userinfobot
ADMIN_IDS = [int(admin_id) for admin_id in os.environ.get("ADMIN_IDS", "123456789").split(',')]


# --- DATABASE CONFIGURATION ---
# Using SQLite for simplicity, works well on Termux and VPS.
# For production, you might want to switch to PostgreSQL.
DATABASE_NAME = "bot_database.db"
DATABASE_URL = f"sqlite:///{DATABASE_NAME}"


# --- SUBSCRIPTION CONFIGURATION ---
DEFAULT_SUB_PRICE = 30  # Default price in INR
TRIAL_PERIOD_DAYS = 3 # Days a new user can use the bot for free before subscription is required


# --- TASK & STRIKE CONFIGURATION ---
MAX_VIDEOS_PER_USER = 5
PROOF_REVIEW_TIMEOUT_MINUTES = 20 # Time in minutes for a user to review a proof
MAX_STRIKES = 4 # Number of strikes before a ban


# --- BOT SETTINGS (Can be controlled by Admin) ---
# These are the default values. Admin can change them via bot commands.
class BotSettings:
    def __init__(self):
        self.subscription_mode = False
        self.ai_moderation_mode = False

# Create a single instance of settings to be used across the bot
bot_settings = BotSettings()

