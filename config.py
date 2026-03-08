import os
from dotenv import load_dotenv

load_dotenv()


def parse_admin_ids(value: str) -> set[int]:
    ids = set()
    for item in value.split(","):
        item = item.strip()
        if item.isdigit():
            ids.add(int(item))
    return ids


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = parse_admin_ids(os.getenv("ADMIN_IDS", ""))

MAIN_CHANNEL_URL = os.getenv("MAIN_CHANNEL_URL", "").strip()
PLAYLISTS_URL = os.getenv("PLAYLISTS_URL", "").strip()
SUPPORT_CONTACT_URL = os.getenv("SUPPORT_CONTACT_URL", "").strip()
PREMIUM_CHANNEL_LINK = os.getenv("PREMIUM_CHANNEL_LINK", "").strip()

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL", "").strip()

INLINE_PLACEHOLDER = os.getenv("INLINE_PLACEHOLDER", "Search courses...")
PORT = int(os.getenv("PORT", "10000"))

PAGE_SIZE = 5

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")

if not SUPABASE_DB_URL:
    raise ValueError("SUPABASE_DB_URL missing")