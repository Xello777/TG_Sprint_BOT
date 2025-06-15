import logging
from fastapi import FastAPI, Request, HTTPException
from telegram.ext import Application
from app.bot import setup_bot
from app.db import get_db, init_db  # Import init_db
from app.config import TELEGRAM_TOKEN, WEBHOOK_URL
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    logger.debug("Starting up FastAPI application")
    try:
        logger.debug(f"TELEGRAM_TOKEN: {'Set' if TELEGRAM_TOKEN else 'Not set'}")
        logger.debug(f"WEBHOOK_URL: {WEBHOOK_URL}")
        if not TELEGRAM_TOKEN:
            logger.error("TELEGRAM_TOKEN is not set")
            raise ValueError("TELEGRAM_TOKEN is not set")
        if not WEBHOOK_URL:
            logger.error("WEBHOOK_URL is not set")
            raise ValueError("WEBHOOK_URL is not set")

        logger.debug("Initializing database")
        init_db()  # Create database tables
        logger.debug("Database initialized")

        logger.debug("Initializing Telegram bot application")
        telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

        logger.debug("Initializing database session")
        with next(get_db()) as db:  # Use context manager
            logger.debug("Database session initialized")
            logger.debug("Setting up bot handlers")
            setup_bot(telegram_app, db)

        logger.debug(f"Setting webhook to {WEBHOOK_URL}")
        await telegram_app.bot.setWebhook(WEBHOOK_URL)
        logger.debug("Webhook set successfully")

        logger.debug("Starting Telegram bot polling")
        await telegram_app.initialize()
        app.state.telegram_app = telegram_app
        logger.debug("Startup completed successfully")
    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    logger.debug("Shutting down FastAPI application")
    try:
        if hasattr(app.state, "telegram_app"):
            logger.debug("Stopping Telegram bot")
            await app.state.telegram_app.stop()
            await app.state.telegram_app.shutdown()
        logger.debug("Shutdown completed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)

@app.post("/webhook")
async def webhook(request: Request):
    logger.debug("Received webhook request")
    try:
        telegram_app = app.state.telegram_app
        update = await request.json()
        logger.debug(f"Webhook update: {update}")
        await telegram_app.process_update(update)
        logger.debug("Webhook processed successfully")
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    logger.debug("Health check requested")
    return {"status": "healthy"}
