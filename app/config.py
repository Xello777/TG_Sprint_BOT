from dotenv import load_dotenv
import os
from typing import Optional, List

load_dotenv()

def get_env_var(name: str, optional: bool = False) -> str:
    value = os.getenv(name)
    if value is None and not optional:
        raise ValueError(f"Environment variable {name} is not set")
    return value

TELEGRAM_TOKEN = get_env_var("TELEGRAM_TOKEN")
ADMIN_IDS = [int(id) for id in get_env_var("ADMIN_IDS").split(",") if id.strip()] if get_env_var("ADMIN_IDS") else []
if not ADMIN_IDS:
    raise ValueError("ADMIN_IDS must contain at least one valid Telegram user ID")
DATABASE_URL = get_env_var("DATABASE_URL")
WEBHOOK_URL = get_env_var("WEBHOOK_URL")
