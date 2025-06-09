# main.py

import sys
import os
 

from fastapi import FastAPI, Request
from app.config import TELEGRAM_TOKEN
from app.bot import handle_update  # создадим в следующем шаге

app = FastAPI()


@app.post("/")
async def telegram_webhook(req: Request):
    data = await req.json()
    await handle_update(data)
    return {"ok": True}
