import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from bot import start_bot_in_background

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_bot_in_background()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def home():
    return {"status": "Bot is running!"}


@app.get("/health")
async def health():
    return {"status": "ok"}