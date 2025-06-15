from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application
from app.bot import setup_bot
from app.db import init_db, get_db
from app.config import TELEGRAM_TOKEN, WEBHOOK_URL

app = FastAPI()

@app.on_event("startup")
async def startup():
    init_db()
    db = next(get_db())
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    setup_bot(telegram_app, db)
    await telegram_app.bot.set_webhook(WEBHOOK_URL)
    app.state.telegram_app = telegram_app

@app.post("/webhook")
async def webhook(request: Request):
    update = Update.de_json(await request.json(), app.state.telegram_app.bot)
    await app.state.telegram_app.process_update(update)
    return {"status": "ok"}
