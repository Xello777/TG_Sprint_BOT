import logging
from app.db import get_active_sprints, add_word
from app.filters import clean_input, is_valid_input
from app.lang_detect import detect_language
from app.config import ADMIN_IDS, DEBUG_MODE
import httpx

logger = logging.getLogger()
logger.setLevel(logging.DEBUG if DEBUG_MODE else logging.WARNING)

async def send_message(chat_id: int, text: str):
    from app.config import TELEGRAM_TOKEN
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={"chat_id": chat_id, "text": text})

async def handle_update(data: dict):
    logging.warning("Handle update called!")
    if "message" not in data:
        return

    msg = data["message"]
    user = msg.get("from", {})
    user_id = user.get("id")
    text = msg.get("text", "")

    logging.warning(f"User ID: {user_id}")
    logging.warning(f"Text: {text}")

    if not text or not user_id:
        return

    if user_id in ADMIN_IDS and text.lower().strip() in ["/debug on", "/debug off"]:
        new_mode = "on" if "on" in text else "off"
        with open(".env", "r") as f:
            lines = f.readlines()
        with open(".env", "w") as f:
            for line in lines:
                if line.startswith("DEBUG_MODE"):
                    f.write(f"DEBUG_MODE={new_mode}\n")
                else:
                    f.write(line)
        await send_message(user_id, f"Debug mode turned {new_mode}")
        return

    words = clean_input(text)
    logging.warning(f"Cleaned words: {words}")
    if not is_valid_input(words):
        logging.warning("Invalid input (bad format or profanity)")
        return

    language = detect_language(text)
    logging.warning(f"Detected language: {language}")
    if language == "unknown":
        return

    sprint_ids = get_active_sprints()
    logging.warning(f"Active sprint IDs: {sprint_ids}")
    if not sprint_ids:
        logging.warning("No active sprints found")
        return

    for sprint_id in sprint_ids:
        for word in words:
            add_word(user_id, sprint_id, word, language)
            logging.warning(f"Added word '{word}' for user {user_id} in sprint {sprint_id}")
