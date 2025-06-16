from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from telegram import Update
from telegram.ext import Application
from app.bot import setup_bot
import logging
import os
import asyncio

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()
telegram_app = None
db = None

@app.on_event("startup")
async def startup_event():
    global telegram_app, db
    logger.debug("Starting up application")
    try:
        # Initialize Telegram bot
        telegram_app = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()
        from app.database import SessionLocal
        db = SessionLocal()
        setup_bot(telegram_app, db)
        logger.debug("Telegram bot initialized")

        # Set webhook
        webhook_url = f"{os.getenv('WEBHOOK_URL')}/webhook"
        await telegram_app.bot.set_webhook(webhook_url)
        logger.debug(f"Webhook set to {webhook_url}")

        # Start the application
        await telegram_app.initialize()
        await telegram_app.start()
        logger.debug("Telegram application started")
    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    global telegram_app, db
    logger.debug("Shutting down application")
    try:
        if telegram_app:
            await telegram_app.stop()
            await telegram_app.shutdown()
            logger.debug("Telegram application stopped")
        if db:
            db.close()
            logger.debug("Database session closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)

@app.post("/webhook")
async def webhook(request: Request):
    logger.debug("Received webhook request")
    try:
        json_data = await request.json()
        logger.debug(f"Parsed Telegram update: {json_data}")
        update = Update.de_json(json_data, telegram_app.bot)
        if update.message and update.message.text:
            logger.debug(f"Update contains command: {update.message.text.startswith('/')}")
            logger.debug(f"Dispatching update with text: '{update.message.text}'")
        await telegram_app.process_update(update)
        logger.debug("Webhook processed successfully")
        return JSONResponse(content={"ok": True})
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok"}
