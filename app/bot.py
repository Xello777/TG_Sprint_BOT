import logging
import httpx
from app.db import get_active_sprints, add_word
from app.filters import clean_input, is_valid_input
from app.lang_detect import detect_language
from app.config import TELEGRAM_TOKEN, ADMIN_IDS, DEBUG_MODE

BOT_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/"

def log_debug(msg: str):
    if DEBUG_MODE:
        logging.warning(msg)

async def send_message(chat_id: int, text: str):
    async with httpx.AsyncClient() as client:
        await client.post(f"{BOT_API}sendMessage", json={"chat_id": chat_id, "text": text})

async def handle_update(data: dict):
    log_debug("Handle update called!")
    if "message" not in data:
        return

    msg = data["message"]
    user_id = msg.get("from", {}).get("id")
    text = msg.get("text", "")
    chat_id = msg.get("chat", {}).get("id")

    log_debug(f"User ID: {user_id}")
    log_debug(f"Text: {text}")

    if not text or not user_id:
        return

    if text.startswith("/start"):
        if user_id in ADMIN_IDS:
            await send_message(chat_id, "Команды администратора:\n/start\n/start_sprint <days> <topic>\n/end_sprint <id>\n/debug on|off")
        else:
            sprints = get_active_sprints()
            if sprints:
                await send_message(chat_id, f"Активные спринты: {', '.join(map(str, sprints))}")
            else:
                await send_message(chat_id, "Сейчас нет активных спринтов.")
        return

    if user_id not in ADMIN_IDS:
        words = clean_input(text)
        log_debug(f"Cleaned words: {words}")
        if not is_valid_input(words):
            log_debug("Invalid input (bad format or profanity)")
            return

        lang = detect_language(text)
        log_debug(f"Detected language: {lang}")
        if lang == "unknown":
            return

        sprint_ids = get_active_sprints()
        log_debug(f"Active sprint IDs: {sprint_ids}")
        if not sprint_ids:
            return

        for sprint_id in sprint_ids:
            for word in words:
                add_word(user_id, sprint_id, word, lang)
                log_debug(f"Saved word: {word} to sprint {sprint_id}")
        return

    if text.startswith("/debug "):
        from app.config import os
        state = text.split("/debug ", 1)[1].strip().lower()
        os.environ["DEBUG"] = "true" if state == "on" else "false"
        await send_message(chat_id, f"Debug mode {'enabled' if state == 'on' else 'disabled'}.")
