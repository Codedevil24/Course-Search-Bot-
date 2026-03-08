import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DB_PATH = os.getenv("DB_PATH", "courses.db")
MAIN_CHANNEL_URL = os.getenv("MAIN_CHANNEL_URL", "https://t.me/Code_Devil")
PLAYLISTS_URL = os.getenv("PLAYLISTS_URL", "https://t.me/addlist/wTBxgyESacMwMDA1")

ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

