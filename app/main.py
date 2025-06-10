from fastapi import FastAPI, Request
from app.config import TELEGRAM_TOKEN, DEBUG_MODE
from app.bot import handle_update
from app.db import start_sprint, get_active_sprints, get_words_for_sprint

app = FastAPI()

@app.post("/")
async def telegram_webhook(req: Request):
    data = await req.json()
    await handle_update(data)
    return {"ok": True}

@app.get("/debug/sprints")
def debug_sprints():
    return {"active_sprints": get_active_sprints()}

@app.get("/debug/start")
def debug_start():
    sprint_id = start_sprint(7, "Debug Sprint")
    return {"sprint_id": sprint_id}

@app.get("/debug/words/{sprint_id}")
def debug_words(sprint_id: int):
    return {"words": get_words_for_sprint(sprint_id)}
