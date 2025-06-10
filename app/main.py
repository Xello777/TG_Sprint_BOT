from fastapi import FastAPI, Request
from .config import TELEGRAM_TOKEN
from .bot import handle_update

app = FastAPI()

@app.post("/")
async def telegram_webhook(req: Request):
    data = await req.json()
    await handle_update(data)
    return {"ok": True}


from app.db import get_words_for_sprint

@app.get("/debug/words/{sprint_id}")
async def debug_words(sprint_id: int):
    words = get_words_for_sprint(sprint_id)
    return {"sprint_id": sprint_id, "words": words}
