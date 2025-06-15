import os
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Telegram Bot Token
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Admin IDs
raw_admin_ids = os.getenv("ADMIN_IDS", "")
logger.debug(f"Raw ADMIN_IDS from env: '{raw_admin_ids}'")
try:
    ADMIN_IDS = [int(x) for x in raw_admin_ids.split(",") if x]
except ValueError as e:
    logger.error(f"Error parsing ADMIN_IDS: {e}")
    ADMIN_IDS = []
logger.debug(f"Parsed ADMIN_IDS: {ADMIN_IDS}")
logger.debug(f"Admin IDs list: {', '.join(str(id) for id in ADMIN_IDS) if ADMIN_IDS else 'No admin IDs'}")

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///sprintbot.db")

# Webhook URL
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
