from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import Application
from app.bot import setup_bot
from app.db import init_db, get_db
from app.config import TELEGRAM_TOKEN, WEBHOOK_URL
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.on_event("startup")
async def startup():
    try:
        init_db()
        telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
        with get_db() as db:
            setup_bot(telegram_app, db)
        await telegram_app.initialize()
        await telegram_app.bot.set_webhook(WEBHOOK_URL)
        app.state.telegram_app = telegram_app
        logger.info("Application started and webhook set")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("shutdown")
async def shutdown():
    if hasattr(app.state, "telegram_app"):
        await app.state.telegram_app.shutdown()
        logger.info("Application shutdown")

@app.post("/webhook")
async def webhook(request: Request):
    try:
        update = Update.de_json(await request.json(), app.state.telegram_app.bot)
        await app.state.telegram_app.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
