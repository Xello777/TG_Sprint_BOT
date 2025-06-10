# main.py

import sys
import os
 

from fastapi import FastAPI, Request
from app.bot import handle_update  # создадим в следующем шаге
from app.сonfig import TELEGRAM_TOKEN  #app/сonfig.py

app = FastAPI()


@app.post("/")
async def telegram_webhook(req: Request):
    data = await req.json()
    await handle_update(data)
    return {"ok": True}
