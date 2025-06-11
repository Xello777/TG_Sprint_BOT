from fastapi import FastAPI, Request
from app.bot import handle_update

app = FastAPI()

@app.post("/")
async def telegram_webhook(req: Request):
    data = await req.json()
    await handle_update(data)
    return {"ok": True}
