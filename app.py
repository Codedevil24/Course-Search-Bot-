import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from bot import start_bot_in_background

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info('FastAPI lifespan startup.')
    start_bot_in_background()
    yield
    logger.info('FastAPI lifespan shutdown.')


app = FastAPI(lifespan=lifespan)


@app.get('/')
async def home():
    return {'status': 'Bot is running!'}


@app.get('/health')
async def health():
    return {'status': 'ok'}
