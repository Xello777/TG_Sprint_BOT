# main.py

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from fastapi import FastAPI, Request
from config import TELEGRAM_TOKEN
from bot import handle_update  # создадим в следующем шаге

app = FastAPI()


@app.post("/")
async def telegram_webhook(req: Request):
    data = await req.json()
    await handle_update(data)
    return {"ok": True}
