import logging

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN, DB_PATH
from db import Database
from handlers import BotHandlers

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN missing. Please set it in .env")

    db = Database(DB_PATH)
    db.init_db()
    db.seed_demo_data()

    bot_handlers = BotHandlers(db)

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", bot_handlers.start))
    app.add_handler(CommandHandler("help", bot_handlers.help_command))
    app.add_handler(CommandHandler("search", bot_handlers.search_command))
    app.add_handler(CommandHandler("categories", bot_handlers.categories))
    app.add_handler(CommandHandler("featured", bot_handlers.featured))

    app.add_handler(CommandHandler("addcourse", bot_handlers.addcourse))
    app.add_handler(CommandHandler("editcourse", bot_handlers.editcourse))
    app.add_handler(CommandHandler("deletecourse", bot_handlers.deletecourse))
    app.add_handler(CommandHandler("listcourses", bot_handlers.listcourses))
    app.add_handler(CommandHandler("feature", bot_handlers.feature))
    app.add_handler(CommandHandler("unfeature", bot_handlers.unfeature))
    app.add_handler(CommandHandler("stats", bot_handlers.stats))

    app.add_handler(CallbackQueryHandler(bot_handlers.button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_handlers.text_search))

    print("Bot is running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()