from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from db import Database
from keyboards import course_keyboard, categories_keyboard, search_results_keyboard, suggestions_keyboard
from services import SearchService
from utils import is_admin, format_course_caption
from config import PREMIUM_CHANNEL_LINK
from csv_importer import import_courses_from_csv


class BotHandlers:
    def __init__(self, db: Database):
        self.db = db
        self.search_service = SearchService(db)

    def track_user(self, update: Update):
        user = update.effective_user
        if user:
            self.db.upsert_user(
                user_id=user.id,
                username=user.username or "",
                first_name=user.first_name or "",
                last_name=user.last_name or "",
            )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        text = (
            "🚀 <b>Welcome to Code Devil Premium Course Bot</b>\n\n"
            "Yahan aap direct course search kar sakte ho.\n\n"
            "Examples:\n"
            "• /search python\n"
            "• /search flutter\n"
            "• krish naik\n"
            "• dsa\n\n"
            "Commands:\n"
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
        self.track_user(update)
        text = (
            "📖 <b>Help</b>\n\n"
            "User:\n"
            "• /search &lt;keyword&gt;\n"
            "• /categories\n"
            "• /featured\n"
            "• normal text search bhi kaam karega\n\n"
            "Admin:\n"
            "• /addcourse\n"
            "• /deletecourse\n"
            "• /listcourses\n"
            "• /feature\n"
            "• /unfeature\n"
            "• /stats\n"
            "• /grant\n"
            "• /importcsv"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)

    async def featured(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
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
        self.track_user(update)
        cats = self.db.get_categories()
        await update.message.reply_text(
            "📚 <b>Categories</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=categories_keyboard(cats),
        )

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
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
        self.track_user(update)
        if not update.message or not update.message.text:
            return
        text = update.message.text.strip()
        if text.startswith("/"):
            return
        if len(text) < 2:
            return
        await self.run_search(update, context, text)

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        query = update.callback_query
        await query.answer()
        data = query.data or ""
        user = update.effective_user

        if data.startswith("course::"):
            course_id = int(data.split("::", 1)[1])
            course = self.db.get_course(course_id)
            if not course:
                await query.edit_message_text("Course not found.")
                return

            self.db.log_click(user.id if user else None, user.username if user else "", course_id, "open_course")

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
        user = update.effective_user
        if user:
            self.db.upsert_user(
                user_id=user.id,
                username=user.username or "",
                first_name=user.first_name or "",
                last_name=user.last_name or "",
            )

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
    self.track_user(update)

    user = update.effective_user
    if not user or not is_admin(user.id):
        await update.message.reply_text("❌ Admin only command.")
        return

    text = update.message.text.replace("/addcourse", "").strip()

    fields = {}

    for line in text.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip().lower()] = value.strip()

    required = ["title", "instructor", "category", "description"]

    for r in required:
        if r not in fields:
            await update.message.reply_text(f"❌ Missing field: {r}")
            return

    keywords = [
        k.strip()
        for k in fields.get("keywords", "").split(",")
        if k.strip()
    ]

    course_id = self.db.add_course(
        title=fields.get("title"),
        instructor=fields.get("instructor"),
        category=fields.get("category"),
        description=fields.get("description"),
        thumbnail_url=fields.get("thumbnail", ""),
        download_url=fields.get("download", ""),
        how_to_download_url=fields.get("howtodownload", ""),
        demo_url=fields.get("demo", ""),
        contact_url=fields.get("contact", ""),
        premium_channel_link=fields.get("premiumlink", ""),
        is_featured=int(fields.get("featured", "0")),
        is_paid=int(fields.get("paid", "0")),
        price=fields.get("price", ""),
        keywords=keywords,
    )

    await update.message.reply_text(
        f"✅ Course Added Successfully\n\n"
        f"📚 Title: {fields.get('title')}\n"
        f"🧑‍🏫 Instructor: {fields.get('instructor')}\n"
        f"📁 Category: {fields.get('category')}\n"
        f"🆔 Course ID: {course_id}"
    )
        

    async def importcsv(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        user = update.effective_user
        if not user or not is_admin(user.id):
            await update.message.reply_text("❌ Admin only command.")
            return

        args = context.args
        if not args:
            await update.message.reply_text("Usage:\n/importcsv sample_courses.csv")
            return

        csv_path = " ".join(args).strip()
        try:
            count = import_courses_from_csv(self.db, csv_path)
            await update.message.reply_text(f"✅ Imported {count} courses from CSV.")
        except Exception as e:
            await update.message.reply_text(f"❌ CSV import failed:\n{e}")

    async def deletecourse(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
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
        self.track_user(update)
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
        self.track_user(update)
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
        self.track_user(update)
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
        self.track_user(update)
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
            f"Total Users: {s['total_users']}",
            f"24h Active Users: {s['active_24h']}",
            f"7d Active Users: {s['active_7d']}",
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

        await update.message.reply_text("\n".join(lines[:180]), parse_mode=ParseMode.HTML)

    async def grant(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
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
                await update.message.reply_text(f"Approved but DM nahi gaya: {e}")
        else:
            await update.message.reply_text("Approved, but premium link not configured.")