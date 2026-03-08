import threading
import logging
from flask import Flask

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    InlineQueryHandler,
    filters,
)

from config import BOT_TOKEN, PORT
from db import Database
from handlers import BotHandlers

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "Bot is running!"


def run_web():
    web_app.run(host="0.0.0.0", port=PORT)


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

    db.add_course(
        title="Code Devil Premium Full Stack Course",
        instructor="Code Devil",
        category="Web Development",
        description="Premium full stack course with project support.",
        thumbnail="https://dummyimage.com/600x400/111/fff&text=Premium+Full+Stack",
        download_url="",
        how_to_download_url="",
        demo_url="https://t.me/Code_Devil",
        contact_url="https://t.me/Code_Devil",
        premium_channel_link="https://t.me/+your_private_invite",
        is_featured=True,
        is_paid=True,
        price="₹999",
        keywords=["code devil premium", "premium full stack", "codedevil course"],
    )


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN missing in .env")

    db = Database()
    db.init_db()
    seed_data(db)

    h = BotHandlers(db)

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", h.start))
    app.add_handler(CommandHandler("help", h.help_command))
    app.add_handler(CommandHandler("search", h.search_command))
    app.add_handler(CommandHandler("categories", h.categories))
    app.add_handler(CommandHandler("featured", h.featured))
    app.add_handler(CommandHandler("addcourse", h.addcourse))
    app.add_handler(CommandHandler("importcsv", h.importcsv))
    app.add_handler(CommandHandler("deletecourse", h.deletecourse))
    app.add_handler(CommandHandler("listcourses", h.listcourses))
    app.add_handler(CommandHandler("feature", h.feature))
    app.add_handler(CommandHandler("unfeature", h.unfeature))
    app.add_handler(CommandHandler("stats", h.stats))
    app.add_handler(CommandHandler("grant", h.grant))

    app.add_handler(CallbackQueryHandler(h.button_handler))
    app.add_handler(InlineQueryHandler(h.inline_query))
    app.add_handler(MessageHandler(filters.PHOTO, h.save_thumbnail))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, h.text_search))

    print("Bot v2.4 is running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    main()