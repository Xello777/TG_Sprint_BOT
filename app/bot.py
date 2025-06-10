import logging
from app.db import get_active_sprints, add_word
from app.filters import clean_input, is_valid_input
from app.lang_detect import detect_language


async def handle_update(data: dict):
    logging.warning("Handle update called!")

    if "message" not in data:
        logging.warning("No 'message' in data")
        return

    msg = data["message"]
    user = msg.get("from", {})
    user_id = user.get("id")
    text = msg.get("text", "")

    logging.warning(f"User ID: {user_id}")
    logging.warning(f"Text: {text}")

    if not text or not user_id:
        logging.warning("Missing user_id or text")
        return

    words = clean_input(text)
    logging.warning(f"Cleaned words: {words}")

    if not is_valid_input(words):
        logging.warning("Invalid input (bad format or profanity)")
        return

    language = detect_language(text)
    logging.warning(f"Detected language: {language}")

    if language == "unknown":
        logging.warning("Language not supported or could not detect")
        return

    sprint_ids = get_active_sprints()
    logging.warning(f"Active sprint IDs: {sprint_ids}")

    if not sprint_ids:
        logging.warning("No active sprints found")
        return

    for sprint_id in sprint_ids:
        for word in words:
            logging.warning(f"Adding word '{word}' to sprint {sprint_id}")
            add_word(user_id, sprint_id, word, language)

    logging.warning("Words successfully added")
