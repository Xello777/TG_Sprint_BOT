from app.db import get_active_sprints, add_word
from app.filters import clean_input, is_valid_input
from app.lang_detect import detect_language

import logging
logging.basicConfig(level=logging.INFO)

async def handle_update(data: dict):
    logging.info("[📥] handle_update вызван")

async def handle_update(data: dict):
    if "message" not in data:
        return

    msg = data["message"]
    user = msg.get("from", {})
    user_id = user.get("id")
    text = msg.get("text", "")

    if not text or not user_id:
        return

    words = clean_input(text)
    if not is_valid_input(words):
        return

    language = detect_language(text)
    if language == "unknown":
        return

    sprint_ids = get_active_sprints()
    for sprint_id in sprint_ids:
        for word in words:
            add_word(user_id, sprint_id, word, language)
            logging.info(f"[✅] Saved word '{word}' from user {user_id} in sprint {sprint_id} ({language})")
