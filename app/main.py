from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from telegram import Update
from telegram.ext import Application
from app.bot import setup_bot
from app.database import SessionLocal, engine
from app.models import Base
import logging
import os
import asyncio
import uvicorn

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()
telegram_app = None
db_session = None

@app.on_event("startup")
async def startup_event():
    global telegram_app, db_session
    logger.debug("Starting up application")
    try:
        # Create database tables
        Base.metadata.create_all(bind=engine)
        logger.debug("Database tables created")

        # Initialize database session
        db_session = SessionLocal()
        logger.debug("Database session initialized")

        # Initialize Telegram bot
        telegram_app = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()
        setup_bot(telegram_app, db_session)
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
    global telegram_app, db_session
    logger.debug("Shutting down application")
    try:
        if telegram_app:
            await telegram_app.stop()
            await telegram_app.shutdown()
            logger.debug("Telegram application stopped")
        if db_session:
            db_session.close()
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
        await telegram_app.process_update(update)
        logger.debug("Webhook processed successfully")
        return JSONResponse(content={"ok": True})
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
