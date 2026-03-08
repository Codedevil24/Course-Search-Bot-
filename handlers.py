from telegram import (
    Update,
    InlineQueryResultArticle,
    InputTextMessageContent,
)
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from db import Database
from keyboards import (
    course_keyboard,
    categories_keyboard,
    search_results_keyboard,
    suggestions_keyboard,
)
from services import SearchService
from utils import is_admin, format_course_caption
from config import PREMIUM_CHANNEL_LINK


class BotHandlers:
    def __init__(self, db: Database):
        self.db = db
        self.search_service = SearchService(db)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "🚀 <b>Welcome to Code Devil Premium Course Bot</b>\n\n"
            "Commands:\n"
            "/search python\n"
            "/categories\n"
            "/featured\n"
            "/help"
        )
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=categories_keyboard(self.db.get_categories())
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "📖 <b>Help</b>\n\n"
            "User commands:\n"
            "• /search &lt;keyword&gt;\n"
            "• /categories\n"
            "• /featured\n\n"
            "Admin commands:\n"
            "• /addcourse\n"
            "• /deletecourse\n"
            "• /listcourses\n"
            "• /feature\n"
            "• /unfeature\n"
            "• /stats\n"
            "• /grant"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)

    async def featured(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        results = self.db.get_featured_courses()
        if not results:
            await update.message.reply_text("Abhi koi featured course nahi hai.")
            return

        await update.message.reply_text(
            "⭐ <b>Featured Courses</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=search_results_keyboard(results),
        )

    async def categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        cats = self.db.get_categories()
        await update.message.reply_text(
            "📚 <b>Categories</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=categories_keyboard(cats),
        )

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = " ".join(context.args).strip()
        if not query:
            await update.message.reply_text("Usage:\n/search python")
            return
        await self.run_search(update, context, query)

    async def run_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
        result = self.search_service.search_with_suggestions(query)
        results = result["results"]
        suggestions = result["suggestions"]

        user = update.effective_user
        self.db.log_search(
            user_id=user.id if user else None,
            username=user.username if user and user.username else "",
            query=query,
            matched_count=len(results),
        )

        if results:
            if len(results) == 1:
                await self.send_course_card(update, results[0])
                return

            await update.message.reply_text(
                f"🔎 <b>{query}</b> ke liye {len(results)} matching courses mile.",
                parse_mode=ParseMode.HTML,
                reply_markup=search_results_keyboard(results),
            )
            return

        if suggestions:
            await update.message.reply_text(
                "❌ Exact result nahi mila.\n\nShayad aap yeh dhundh rahe the:",
                reply_markup=suggestions_keyboard(suggestions),
            )
            return

        await update.message.reply_text("❌ Koi course nahi mila.")

    async def send_course_card(self, update: Update, course: dict):
        caption = format_course_caption(course)
        if course.get("thumbnail_url"):
            await update.message.reply_photo(
                photo=course["thumbnail_url"],
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=course_keyboard(course),
            )
        else:
            await update.message.reply_text(
                caption,
                parse_mode=ParseMode.HTML,
                reply_markup=course_keyboard(course),
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

            caption = format_course_caption(course)
            if course.get("thumbnail_url"):
                await query.message.reply_photo(
                    photo=course["thumbnail_url"],
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=course_keyboard(course),
                )
            else:
                await query.edit_message_text(
                    caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=course_keyboard(course),
                )
            return

        if data.startswith("cat::"):
            category = data.split("::", 1)[1]
            results = self.db.search_courses(category, limit=20)
            await query.edit_message_text(
                f"🗂 <b>{category}</b> category ke courses:",
                parse_mode=ParseMode.HTML,
                reply_markup=search_results_keyboard(results),
            )
            return

        if data.startswith("suggest::"):
            keyword = data.split("::", 1)[1]
            results = self.db.search_courses(keyword, limit=10)
            await query.edit_message_text(
                f"🔎 Suggested results for <b>{keyword}</b>:",
                parse_mode=ParseMode.HTML,
                reply_markup=search_results_keyboard(results),
            )
            return

        if data.startswith("premium::"):
            course_id = int(data.split("::", 1)[1])
            course = self.db.get_course(course_id)
            if not course:
                await query.edit_message_text("Course not found.")
                return

            link = course.get("premium_channel_link") or PREMIUM_CHANNEL_LINK or "Not configured"
            await query.message.reply_text(
                f"🔓 Premium access manual approval based hai.\n\n"
                f"Course: {course['title']}\n"
                f"Purchase ke baad admin se contact karo.\n"
                f"Approved hone ke baad premium link diya jayega:\n{link}"
            )
            return

        if data == "featured::all":
            results = self.db.get_featured_courses(limit=20)
            await query.edit_message_text(
                "⭐ <b>Featured Courses</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=search_results_keyboard(results),
            )

    async def inline_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.inline_query.query.strip()
        if not query:
            return

        results = self.db.search_courses(query, limit=20)
        inline_results = []

        for course in results:
            desc = f"{course.get('category') or 'General'} | {course.get('instructor') or 'Unknown'}"
            message_text = (
                f"📚 <b>{course['title']}</b>\n"
                f"👨‍🏫 {course.get('instructor') or 'Unknown'}\n"
                f"🗂 {course.get('category') or 'General'}"
            )
            inline_results.append(
                InlineQueryResultArticle(
                    id=str(course["id"]),
                    title=course["title"],
                    description=desc,
                    input_message_content=InputTextMessageContent(
                        message_text=message_text,
                        parse_mode=ParseMode.HTML,
                    ),
                )
            )

        await update.inline_query.answer(inline_results, cache_time=1)

    async def addcourse(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_admin(user.id):
            await update.message.reply_text("❌ Admin only command.")
            return

        text = update.message.text.replace("/addcourse", "", 1).strip()
        parts = [p.strip() for p in text.split("||")]

        if len(parts) != 13:
            await update.message.reply_text(
                "Format:\n"
                "/addcourse title || instructor || category || description || thumbnail_url || download_url || how_to_download_url || demo_url || contact_url || premium_channel_link || is_featured(0/1) || is_paid(0/1) || price || keywords\n\n"
                "Note: last keywords part comma separated manually add karo after price by editing code if needed."
            )
            return

    async def deletecourse(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_admin(user.id):
            await update.message.reply_text("❌ Admin only command.")
            return

        text = update.message.text.replace("/deletecourse", "", 1).strip()
        if not text.isdigit():
            await update.message.reply_text("Usage: /deletecourse 3")
            return
        self.db.delete_course(int(text))
        await update.message.reply_text("🗑 Deleted.")

    async def listcourses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_admin(user.id):
            await update.message.reply_text("❌ Admin only command.")
            return

        courses = self.db.list_courses(limit=100)
        lines = ["📚 <b>Courses</b>"]
        for c in courses:
            lines.append(f"{c['id']}. {c['title']} | Paid: {c['is_paid']} | Featured: {c['is_featured']}")
        await update.message.reply_text("\n".join(lines[:120]), parse_mode=ParseMode.HTML)

    async def feature(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_admin(user.id):
            await update.message.reply_text("❌ Admin only command.")
            return
        text = update.message.text.replace("/feature", "", 1).strip()
        if not text.isdigit():
            await update.message.reply_text("Usage: /feature 2")
            return
        self.db.set_featured(int(text), 1)
        await update.message.reply_text("⭐ Featured enabled.")

    async def unfeature(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_admin(user.id):
            await update.message.reply_text("❌ Admin only command.")
            return
        text = update.message.text.replace("/unfeature", "", 1).strip()
        if not text.isdigit():
            await update.message.reply_text("Usage: /unfeature 2")
            return
        self.db.set_featured(int(text), 0)
        await update.message.reply_text("✅ Featured removed.")

    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_admin(user.id):
            await update.message.reply_text("❌ Admin only command.")
            return

        s = self.db.get_stats()
        lines = [
            "📊 <b>Analytics Dashboard</b>",
            f"Total Courses: {s['total_courses']}",
            f"Paid Courses: {s['total_paid_courses']}",
            f"Total Searches: {s['total_searches']}",
            "",
            "🔥 Top Queries:",
        ]
        for row in s["popular_queries"]:
            lines.append(f"• {row['query']} — {row['c']}")

        lines.append("")
        lines.append("🚫 Zero Result Queries:")
        for row in s["zero_results"]:
            lines.append(f"• {row['query']} — {row['c']}")

        lines.append("")
        lines.append("📈 Top Clicked Courses:")
        for row in s["top_clicked"]:
            lines.append(f"• {row['title']} — {row['ccount']}")

        await update.message.reply_text("\n".join(lines[:150]), parse_mode=ParseMode.HTML)

    async def grant(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_admin(user.id):
            await update.message.reply_text("❌ Admin only command.")
            return

        args = context.args
        if len(args) < 2:
            await update.message.reply_text("Usage: /grant user_id course_id")
            return

        target_user_id = int(args[0])
        course_id = int(args[1])
        course = self.db.get_course(course_id)
        if not course:
            await update.message.reply_text("Course not found.")
            return

        self.db.approve_purchase(target_user_id, course_id, user.id)

        premium_link = course.get("premium_channel_link") or PREMIUM_CHANNEL_LINK
        if premium_link:
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=(
                        f"🎉 Aapka premium access approve ho gaya hai.\n\n"
                        f"Course: {course['title']}\n"
                        f"Join here: {premium_link}"
                    ),
                )
                await update.message.reply_text("✅ Access granted and user notified.")
            except Exception as e:
                await update.message.reply_text(f"Approved but user ko DM nahi gaya: {e}")
        else:
            await update.message.reply_text("Approved, but premium link not configured.")