import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL", "").strip()
MAIN_CHANNEL_URL = os.getenv("MAIN_CHANNEL_URL", "https://t.me/Code_Devil")
PLAYLISTS_URL = os.getenv("PLAYLISTS_URL", "https://t.me/addlist/wTBxgyESacMwMDA1")
SUPPORT_CONTACT_URL = os.getenv("SUPPORT_CONTACT_URL", "https://t.me/Code_Devil")
PREMIUM_CHANNEL_LINK = os.getenv("PREMIUM_CHANNEL_LINK", "")
PORT = int(os.getenv("PORT", "10000"))

ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}