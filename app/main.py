from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from telegram import Update
from telegram.ext import Application
from app.bot import setup_bot
from app.database import SessionLocal
import logging
import os

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

telegram_app = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()
db = SessionLocal()
setup_bot(telegram_app, db)

@app.post("/webhook")
async def webhook(request: Request):
    logger.debug("Webhook received")
    try:
        json_data = await request.json()
        logger.debug(f"Parsed Telegram update: {json_data}")
        update = Update.de_json(json_data, telegram_app.bot)
        if update.message and update.message.text:
            logger.debug(f"Update contains command: {update.message.text.startswith('/')}")
            logger.debug(f"Dispatching update with text: '{update.message.text}'")
        await telegram_app.process_update(update)
        logger.debug("Webhook processed")
        return JSONResponse(content={"ok": True})
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok"}
