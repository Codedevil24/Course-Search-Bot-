from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from db import Database
from keyboards import course_keyboard, categories_keyboard, search_results_keyboard
from utils import is_admin, format_course_caption


class BotHandlers:
    def __init__(self, db: Database):
        self.db = db

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "🚀 <b>Welcome to Code Devil Course Search Bot</b>\n\n"
            "Yeh bot tumhare group ko course search engine ki tarah use karne deta hai.\n\n"
            "Commands:\n"
            "/search python\n"
            "/categories\n"
            "/featured\n"
            "/help"
        )
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=categories_keyboard(self.db.get_categories()),
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "📖 <b>Bot Help</b>\n\n"
            "Public commands:\n"
            "• /search &lt;keyword&gt;\n"
            "• /categories\n"
            "• /featured\n\n"
            "Examples:\n"
            "• /search python\n"
            "• /search flutter\n"
            "• /search krish naik\n\n"
            "Admin commands:\n"
            "• /addcourse\n"
            "• /editcourse\n"
            "• /deletecourse\n"
            "• /listcourses\n"
            "• /feature\n"
            "• /unfeature\n"
            "• /stats"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)

    async def featured(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        results = self.db.get_featured_courses()
        if not results:
            await update.message.reply_text("Abhi koi featured course available nahi hai.")
            return

        await update.message.reply_text(
            "⭐ <b>Featured Courses</b>\nNeeche course select karo:",
            parse_mode=ParseMode.HTML,
            reply_markup=search_results_keyboard(results),
        )

    async def categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        cats = self.db.get_categories()
        if not cats:
            await update.message.reply_text("Abhi koi category available nahi hai.")
            return

        await update.message.reply_text(
            "📚 <b>Categories</b>\nNeeche category select karo:",
            parse_mode=ParseMode.HTML,
            reply_markup=categories_keyboard(cats),
        )

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = " ".join(context.args).strip()
        if not query:
            await update.message.reply_text(
                "Usage:\n/search python\n/search flutter\n/search krish naik"
            )
            return
        await self.run_search(update, context, query)

    async def run_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
        results = self.db.search_courses(query, limit=10)

        user = update.effective_user
        self.db.log_search(
            user_id=user.id if user else None,
            username=user.username if user and user.username else "",
            query=query,
            matched_count=len(results),
        )

        if not results:
            await update.message.reply_text(
                f"❌ '{query}' ke liye koi course nahi mila.\n\n"
                "Try:\n"
                "• short keyword\n"
                "• instructor name\n"
                "• category name"
            )
            return

        if len(results) == 1:
            course = results[0]
            await update.message.reply_text(
                format_course_caption(course),
                parse_mode=ParseMode.HTML,
                reply_markup=course_keyboard(course),
                disable_web_page_preview=False,
            )
            return

        await update.message.reply_text(
            f"🔎 <b>{query}</b> ke liye {len(results)} matching courses mile.\nNeeche select karo:",
            parse_mode=ParseMode.HTML,
            reply_markup=search_results_keyboard(results),
        )

    async def text_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            return

        text = update.message.text.strip()
        if text.startswith("/"):
            return
        if len(text) < 2:
            return

        await self.run_search(update, context, text)

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        data = query.data or ""

        if data.startswith("course::"):
            course_id = int(data.split("::", 1)[1])
            course = self.db.get_course(course_id)

            if not course:
                await query.edit_message_text("Course not found.")
                return

            await query.edit_message_text(
                format_course_caption(course),
                parse_mode=ParseMode.HTML,
                reply_markup=course_keyboard(course),
            )
            return

        if data.startswith("cat::"):
            category = data.split("::", 1)[1]
            results = self.db.search_courses(category, limit=20)

            if not results:
                await query.edit_message_text(f"{category} category me abhi koi course nahi mila.")
                return

            await query.edit_message_text(
                f"🗂 <b>{category}</b> category ke courses:",
                parse_mode=ParseMode.HTML,
                reply_markup=search_results_keyboard(results),
            )
            return

        if data == "featured::all":
            results = self.db.get_featured_courses(limit=20)
            if not results:
                await query.edit_message_text("Abhi koi featured course nahi hai.")
                return

            await query.edit_message_text(
                "⭐ <b>Featured Courses</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=search_results_keyboard(results),
            )

    async def addcourse(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_admin(user.id):
            await update.message.reply_text("❌ Admin only command.")
            return

        text = update.message.text.replace("/addcourse", "", 1).strip()
        parts = [p.strip() for p in text.split("||")]

        if len(parts) != 7:
            await update.message.reply_text(
                "Format:\n"
                "/addcourse title || instructor || category || description || download_url || how_to_download_url || keyword1,keyword2,keyword3"
            )
            return

        title, instructor, category, description, download_url, how_url, keywords_raw = parts
        keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]

        course_id = self.db.add_course(
            title=title,
            instructor=instructor,
            category=category,
            description=description,
            download_url=download_url,
            how_to_download_url=how_url,
            keywords=keywords,
        )

        await update.message.reply_text(f"✅ Course added successfully. ID: {course_id}")

    async def editcourse(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_admin(user.id):
            await update.message.reply_text("❌ Admin only command.")
            return

        text = update.message.text.replace("/editcourse", "", 1).strip()
        parts = [p.strip() for p in text.split("||")]

        if len(parts) != 7:
            await update.message.reply_text(
                "Format:\n"
                "/editcourse id || title || instructor || category || description || download_url || how_to_download_url"
            )
            return

        course_id, title, instructor, category, description, download_url, how_url = parts

        if not course_id.isdigit():
            await update.message.reply_text("Invalid course ID.")
            return

        self.db.update_course(
            course_id=int(course_id),
            title=title,
            instructor=instructor,
            category=category,
            description=description,
            download_url=download_url,
            how_to_download_url=how_url,
        )

        await update.message.reply_text("✅ Course updated successfully.")

    async def deletecourse(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_admin(user.id):
            await update.message.reply_text("❌ Admin only command.")
            return

        text = update.message.text.replace("/deletecourse", "", 1).strip()
        if not text.isdigit():
            await update.message.reply_text("Usage:\n/deletecourse 2")
            return

        self.db.delete_course(int(text))
        await update.message.reply_text("🗑 Course deleted successfully.")

    async def listcourses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_admin(user.id):
            await update.message.reply_text("❌ Admin only command.")
            return

        courses = self.db.list_courses(limit=100)
        if not courses:
            await update.message.reply_text("No courses found.")
            return

        lines = ["📚 <b>Courses List</b>\n"]
        for c in courses:
            lines.append(f"{c['id']}. {c['title']} | {c.get('category') or 'General'}")

        await update.message.reply_text("\n".join(lines[:120]), parse_mode=ParseMode.HTML)

    async def feature(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_admin(user.id):
            await update.message.reply_text("❌ Admin only command.")
            return

        text = update.message.text.replace("/feature", "", 1).strip()
        if not text.isdigit():
            await update.message.reply_text("Usage:\n/feature 2")
            return

        self.db.set_featured(int(text), 1)
        await update.message.reply_text("⭐ Course marked as featured.")

    async def unfeature(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_admin(user.id):
            await update.message.reply_text("❌ Admin only command.")
            return

        text = update.message.text.replace("/unfeature", "", 1).strip()
        if not text.isdigit():
            await update.message.reply_text("Usage:\n/unfeature 2")
            return

        self.db.set_featured(int(text), 0)
        await update.message.reply_text("✅ Course removed from featured.")

    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_admin(user.id):
            await update.message.reply_text("❌ Admin only command.")
            return

        stats = self.db.get_stats()
        lines = [
            "📊 <b>Bot Stats</b>",
            f"Total Courses: {stats['total_courses']}",
            f"Total Searches: {stats['total_searches']}",
            "",
            "Top Queries:",
        ]

        if stats["popular_queries"]:
            for row in stats["popular_queries"]:
                lines.append(f"• {row['query']} — {row['c']} times")
        else:
            lines.append("• No search data yet")

        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)