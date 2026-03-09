import asyncio
import logging
import threading

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    InlineQueryHandler,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN
from db import Database
from handlers import BotHandlers

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

_bot_thread = None
_bot_started = False


def seed_data(db: Database):
    existing = db.list_courses(limit=1)
    if existing:
        return

    db.add_course(
        title="Codebasics – Deep Learning: Beginner to Advanced",
        instructor="Codebasics",
        category="AI / Deep Learning",
        description="Deep learning course from beginner to advanced.",
        thumbnail="https://dummyimage.com/600x400/000/fff&text=Deep+Learning",
        download_url="https://gplinks.co/Codebasics_deeplearning",
        how_to_download_url="https://youtu.be/_p_SeBnl-xE?si=cgjhCJVNP6O-luir",
        demo_url="",
        contact_url="https://t.me/Code_Devil",
        premium_channel_link="",
        is_featured=True,
        is_paid=False,
        price="",
        keywords=["deep learning", "codebasics dl", "codebasics deep learning"],
    )


async def _run_bot():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN missing in .env")

    logger.info("Initializing bot application...")

    db = Database()
    db.init_db()
    seed_data(db)

    h = BotHandlers(db)

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", h.start))
    application.add_handler(CommandHandler("help", h.help_command))
    application.add_handler(CommandHandler("search", h.search_command))
    application.add_handler(CommandHandler("categories", h.categories))
    application.add_handler(CommandHandler("featured", h.featured))
    application.add_handler(CommandHandler("addcourse", h.addcourse))
    application.add_handler(CommandHandler("importcsv", h.importcsv))
    application.add_handler(CommandHandler("deletecourse", h.deletecourse))
    application.add_handler(CommandHandler("listcourses", h.listcourses))
    application.add_handler(CommandHandler("feature", h.feature))
    application.add_handler(CommandHandler("unfeature", h.unfeature))
    application.add_handler(CommandHandler("stats", h.stats))
    application.add_handler(CommandHandler("grant", h.grant))

    application.add_handler(CallbackQueryHandler(h.button_handler))
    application.add_handler(InlineQueryHandler(h.inline_query))
    application.add_handler(MessageHandler(filters.PHOTO, h.save_thumbnail))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, h.text_search))

    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    logger.info("Bot polling started.")

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


def start_bot_in_background():
    global _bot_thread, _bot_started

    if _bot_started:
        return

    _bot_started = True

    def target():
        asyncio.run(_run_bot())

    _bot_thread = threading.Thread(target=target, daemon=True)
    _bot_thread.start()

    logger.info("Bot background thread started.")
