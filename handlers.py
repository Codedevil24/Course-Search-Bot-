from __future__ import annotations

import logging
from pathlib import Path

from telegram import InputTextMessageContent, InlineQueryResultArticle, Update
from telegram.error import BadRequest
from telegram.constants import ChatType, ParseMode
from telegram.ext import ContextTypes

from config import PAGE_SIZE, PREMIUM_CHANNEL_LINK, ADMIN_IDS
from csv_importer import import_courses_from_csv
from db import Database
from keyboards import categories_keyboard, course_keyboard, home_keyboard, locked_access_keyboard, search_results_keyboard, suggestions_keyboard
from services import SearchService
from utils import (
    escape_html,
    format_course_caption,
    format_inline_course_message,
    get_locked_reply_text,
    get_locked_welcome_text,
    get_unlocked_welcome_text,
    is_admin,
    is_user_joined_required_channels,
)

logger = logging.getLogger(__name__)


class BotHandlers:
    def __init__(self, db: Database):
        self.db = db
        self.search_service = SearchService(db)

    def track_user(self, update: Update):
        user = update.effective_user
        if user:
            self.db.upsert_user(user_id=user.id, username=user.username or '', first_name=user.first_name or '', last_name=user.last_name or '')

    def _is_group_chat(self, update: Update) -> bool:
        chat = update.effective_chat
        return bool(chat and chat.type in (ChatType.GROUP, ChatType.SUPERGROUP))

    async def _reply_user_scoped(self, update: Update, text: str, **kwargs):
        message = update.message
        if not message:
            return
        try:
            if self._is_group_chat(update):
                kwargs.setdefault('reply_to_message_id', message.message_id)
                kwargs.setdefault('allow_sending_without_reply', True)
            await message.reply_text(text, **kwargs)
        except BadRequest:
            kwargs.pop('reply_to_message_id', None)
            kwargs.pop('allow_sending_without_reply', None)
            await message.reply_text(text, **kwargs)


    async def ensure_access(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        user = update.effective_user
        if not user:
            return False
        joined = await is_user_joined_required_channels(context.bot, user.id)
        if joined:
            if not is_admin(user.id):
                maintenance = self.db.get_maintenance_status()
                if maintenance.get('enabled'):
                    text = f"🛠 <b>Maintenance Mode</b>\n\n{escape_html(maintenance.get('message') or 'Bot is under maintenance. Please try again later.')}"
                    if update.message:
                        await self._reply_user_scoped(update, text, parse_mode=ParseMode.HTML)
                    elif update.callback_query and update.callback_query.message:
                        await update.callback_query.message.reply_text(text, parse_mode=ParseMode.HTML)
                    return False
            return True

        text = get_locked_reply_text()
        if update.message:
            await self._reply_user_scoped(update, text, parse_mode=ParseMode.HTML, reply_markup=locked_access_keyboard())
        elif update.callback_query and update.callback_query.message:
            await update.callback_query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=locked_access_keyboard())
        return False

    async def send_start_ui(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        first_name = user.first_name if user else ''
        joined = await is_user_joined_required_channels(context.bot, user.id) if user else False
        if not update.message:
            return
        if joined:
            await self._reply_user_scoped(update, get_unlocked_welcome_text(first_name), parse_mode=ParseMode.HTML, reply_markup=home_keyboard())
        else:
            await self._reply_user_scoped(update, get_locked_welcome_text(first_name), parse_mode=ParseMode.HTML, reply_markup=locked_access_keyboard())

    def _help_text(self, admin: bool) -> str:
        text = """📖 <b>Course Search Bot Help</b>

👤 <b>User Commands</b>
• /start - bot start karo
• /help - help menu kholo
• /search &lt;keyword&gt; - course search karo
• /categories - category wise browse karo
• /featured - featured courses dekho
• /new - recently added courses dekho
• /trending - trending courses dekho
• /saved - saved courses dekho
• /request &lt;course name&gt; - missing course request bhejo

🔎 <b>Search Kaise Kare</b>
• /search python
• /search web development
• Direct text bhi bhej sakte ho: python, harkirat, dsa

📌 <b>Notes</b>
• Typo hone par bot suggestions dikhayega
• Required channels joined hone par direct access mil jayega
• Verify button membership ko recheck karta hai

📢 <b>Official Links</b>
• Telegram: https://t.me/Code_Devil
• Telegram: https://t.me/Devil_Developee
• WhatsApp: https://whatsapp.com/channel/0029VaacxeOKWEKsD2KdqR0U
• YouTube: https://www.youtube.com/@Devil_Coder
• Owner: https://t.me/code_devil24"""
        if admin:
            text += """

🛠 <b>Admin Only Commands</b>
• /admin - quick admin panel
• /addcourse
• /updatecourse
• /deletecourse 12
• /restorecourse 12
• /setthumb 12
• /importcsv sample_courses.csv
• CSV file upload bhi supported hai
• /listcourses
• /feature 12
• /unfeature 12
• /stats
• /pendingpayments
• /grant user_id course_id
• /requests
• /requestdone request_id
• /broadcast your message
• /maintenance on reason
• /maintenance off

🔐 <b>Important</b>
Ye commands sirf admins ke liye visible aur usable hain."""
        return text

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        await self.send_start_ui(update, context)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        if not update.message:
            return
        if not await self.ensure_access(update, context):
            return
        user = update.effective_user
        await self._reply_user_scoped(update, self._help_text(bool(user and is_admin(user.id))), parse_mode=ParseMode.HTML)

    async def categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        if not update.message:
            return
        if not await self.ensure_access(update, context):
            return
        cats = self.db.get_categories()
        if not cats:
            await self._reply_user_scoped(update, '❌ No categories found.')
            return
        await self._reply_user_scoped(update, '📚 <b>Categories</b>', parse_mode=ParseMode.HTML, reply_markup=categories_keyboard(cats, page=0))

    async def featured(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        if not update.message:
            return
        if not await self.ensure_access(update, context):
            return
        await self.send_featured_page(update.message.reply_text, page=0)


    async def request_course(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        user = update.effective_user
        if not update.message or not user:
            return
        if not await self.ensure_access(update, context):
            return
        request_text = ' '.join(context.args).strip()
        if not request_text:
            await self._reply_user_scoped(update, 'Usage:\n/request course name')
            return
        request_id = self.db.add_course_request(user.id, user.username or '', request_text)
        await self._reply_user_scoped(update, f'✅ Request saved successfully.\nRequest ID: {request_id}\n\nCourse request: {request_text}')
        for admin_id in sorted(ADMIN_IDS):
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=(
                        '📥 New course request\n\n'
                        f'ID: <code>{request_id}</code>\n'
                        f'User ID: <code>{user.id}</code>\n'
                        f'Username: @{escape_html(user.username) if user.username else "-"}\n'
                        f'Request: {escape_html(request_text)}\n\n'
                        f'Done: <code>/requestdone {request_id}</code>'
                    ),
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                logger.exception('Failed to notify admin %s for request', admin_id)

    async def saved_courses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        user = update.effective_user
        if not update.message or not user:
            return
        if not await self.ensure_access(update, context):
            return
        total = self.db.count_saved_courses(user.id)
        results = self.db.get_saved_courses(user.id, limit=PAGE_SIZE, offset=0)
        if not results:
            await self._reply_user_scoped(update, '⭐ Aapne abhi tak koi course save nahi kiya.')
            return
        await self._reply_user_scoped(
            update,
            f'⭐ <b>Saved Courses</b>\nTotal: {total}',
            parse_mode=ParseMode.HTML,
            reply_markup=search_results_keyboard(results, 'saved', str(user.id), 0, total),
        )

    async def new_courses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        if not update.message:
            return
        if not await self.ensure_access(update, context):
            return
        total = self.db.count_recent_courses()
        results = self.db.get_recent_courses(limit=PAGE_SIZE, offset=0)
        if not results:
            await self._reply_user_scoped(update, '❌ No courses found.')
            return
        await self._reply_user_scoped(
            update,
            f'🆕 <b>Recently Added Courses</b>\nTotal: {total}',
            parse_mode=ParseMode.HTML,
            reply_markup=search_results_keyboard(results, 'recent', 'all', 0, total),
        )

    async def trending_courses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        if not update.message:
            return
        if not await self.ensure_access(update, context):
            return
        total = self.db.count_trending_courses()
        results = self.db.get_trending_courses(limit=PAGE_SIZE, offset=0)
        if not results:
            await self._reply_user_scoped(update, '❌ No trending courses found.')
            return
        await self._reply_user_scoped(
            update,
            f'🔥 <b>Trending Courses</b>\nTotal: {total}',
            parse_mode=ParseMode.HTML,
            reply_markup=search_results_keyboard(results, 'trending', 'all', 0, total),
        )

    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        user = update.effective_user
        if not user or not is_admin(user.id):
            if update.message:
                await update.message.reply_text('❌ Admin only command.')
            return
        if not update.message:
            return
        await update.message.reply_text(
            '🛠 <b>Admin Panel</b>\n\n'
            'Core:\n'
            '• /addcourse\n• /updatecourse\n• /deletecourse 12\n• /restorecourse 12\n• /setthumb 12\n• /importcsv\n\n'
            'Management:\n'
            '• /listcourses\n• /feature 12\n• /unfeature 12\n• /stats\n\n'
            'Requests & Broadcast:\n'
            '• /requests\n• /requestdone 4\n• /broadcast text\n• /maintenance on reason\n• /maintenance off\n\n'
            'Payments:\n'
            '• /pendingpayments\n• /grant user_id course_id',
            parse_mode=ParseMode.HTML,
        )

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        if not update.message:
            return
        if not await self.ensure_access(update, context):
            return
        query = ' '.join(context.args).strip()
        if not query:
            await self._reply_user_scoped(update, 'Usage:\n/search python')
            return
        await self.run_search(update, query, page=0)

    async def run_search(self, update: Update, query: str, page: int = 0):
        offset = page * PAGE_SIZE
        message = update.message
        if not message:
            return

        try:
            result = self.search_service.search_with_suggestions(query, limit=PAGE_SIZE, offset=offset)
            results = result['results']
            suggestions = result['suggestions']
            total = result['total']
        except Exception:
            logger.exception('Search pipeline failed for query=%s', query)
            await self._reply_user_scoped(update, '❌ Search me temporary problem aa gayi. Thodi der baad phir try karo.')
            return

        user = update.effective_user
        try:
            self.db.log_search(user_id=user.id if user else None, username=user.username if user and user.username else '', query=query, matched_count=total)
        except Exception:
            logger.exception('Failed to log search for query=%s', query)

        if results:
            if total == 1 and page == 0:
                try:
                    self.db.log_click(user.id if user else None, user.username if user and user.username else '', results[0]['id'], 'open_course')
                except Exception:
                    logger.exception('Failed to log click for course_id=%s', results[0].get('id'))
                await self.send_course_card(message.reply_text, message.reply_photo, results[0])
                return
            await self._reply_user_scoped(
                update,
                f'🔎 <b>{escape_html(query)}</b> ke liye {total} matching courses mile.',
                parse_mode=ParseMode.HTML,
                reply_markup=search_results_keyboard(results, 'search', query, page, total),
            )
            return

        if suggestions:
            await self._reply_user_scoped(
                update,
                '❌ Exact result nahi mila.\n\nShayad aap yeh dhundh rahe the:',
                reply_markup=suggestions_keyboard(suggestions),
            )
            return

        await self._reply_user_scoped(update, '❌ Koi course nahi mila.')


    async def send_course_card(self, reply_text_fn, reply_photo_fn, course: dict):
        caption = format_course_caption(course)
        thumbnail = course.get('thumbnail')
        if thumbnail:
            try:
                await reply_photo_fn(photo=thumbnail, caption=caption, parse_mode=ParseMode.HTML, reply_markup=course_keyboard(course))
                return
            except Exception:
                logger.exception('Failed to send thumbnail, falling back to text.')
        await reply_text_fn(caption, parse_mode=ParseMode.HTML, reply_markup=course_keyboard(course))

    async def text_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        if not update.message or not update.message.text:
            return
        if not await self.ensure_access(update, context):
            return
        text = update.message.text.strip()
        if text.startswith('/') or len(text) < 2:
            return
        await self.run_search(update, text, page=0)

    async def send_search_page_callback(self, query, user, search_query: str, page: int):
        result = self.search_service.search_with_suggestions(search_query, limit=PAGE_SIZE, offset=page * PAGE_SIZE)
        total = result['total']
        results = result['results']
        if not results:
            await query.message.reply_text('❌ Is page me koi results nahi mile.')
            return
        await query.edit_message_text(
            f'🔎 <b>{escape_html(search_query)}</b> ke liye {total} matching courses mile.',
            parse_mode=ParseMode.HTML,
            reply_markup=search_results_keyboard(results, 'search', search_query, page, total),
        )

    async def send_category_page(self, query, category: str, page: int):
        total = self.db.count_courses_by_category(category)
        results = self.db.search_courses_by_category(category, limit=PAGE_SIZE, offset=page * PAGE_SIZE)
        if not results:
            await query.message.reply_text('❌ Is category me koi course nahi mila.')
            return
        await query.edit_message_text(
            f'🗂 <b>{escape_html(category)}</b> category ke {total} courses:',
            parse_mode=ParseMode.HTML,
            reply_markup=search_results_keyboard(results, 'category', category, page, total),
        )

    async def send_featured_page(self, responder, page: int):
        total = self.db.count_featured_courses()
        results = self.db.get_featured_courses(limit=PAGE_SIZE, offset=page * PAGE_SIZE)
        if not results:
            await responder('❌ No featured courses found.')
            return
        await responder(
            f'⭐ <b>Featured Courses</b>\nTotal: {total}',
            parse_mode=ParseMode.HTML,
            reply_markup=search_results_keyboard(results, 'featured', 'all', page, total),
        )

    async def send_saved_page(self, query, user_id: int, page: int):
        total = self.db.count_saved_courses(user_id)
        results = self.db.get_saved_courses(user_id, limit=PAGE_SIZE, offset=page * PAGE_SIZE)
        if not results:
            await query.message.reply_text('⭐ Saved list empty hai.')
            return
        await query.edit_message_text(
            f'⭐ <b>Saved Courses</b>\nTotal: {total}',
            parse_mode=ParseMode.HTML,
            reply_markup=search_results_keyboard(results, 'saved', str(user_id), page, total),
        )

    async def send_recent_page(self, query, page: int):
        total = self.db.count_recent_courses()
        results = self.db.get_recent_courses(limit=PAGE_SIZE, offset=page * PAGE_SIZE)
        if not results:
            await query.message.reply_text('❌ No courses found.')
            return
        await query.edit_message_text(
            f'🆕 <b>Recently Added Courses</b>\nTotal: {total}',
            parse_mode=ParseMode.HTML,
            reply_markup=search_results_keyboard(results, 'recent', 'all', page, total),
        )

    async def send_trending_page(self, query, page: int):
        total = self.db.count_trending_courses()
        results = self.db.get_trending_courses(limit=PAGE_SIZE, offset=page * PAGE_SIZE)
        if not results:
            await query.message.reply_text('❌ No trending courses found.')
            return
        await query.edit_message_text(
            f'🔥 <b>Trending Courses</b>\nTotal: {total}',
            parse_mode=ParseMode.HTML,
            reply_markup=search_results_keyboard(results, 'trending', 'all', page, total),
        )

    async def notify_admins_pending_purchase(self, context: ContextTypes.DEFAULT_TYPE, course: dict, user):
        for admin_id in sorted(ADMIN_IDS):
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=(
                        '🧾 New payment request\n\n'
                        f'User ID: <code>{user.id}</code>\n'
                        f'Username: @{escape_html(user.username) if user.username else "-"}\n'
                        f'Course ID: {course["id"]}\n'
                        f'Course: {escape_html(course["title"])}\n\n'
                        f'Grant command: <code>/grant {user.id} {course["id"]}</code>'
                    ),
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                logger.exception('Failed to notify admin %s for pending purchase', admin_id)

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query:
            return
        await query.answer()
        data = query.data or ''
        user = update.effective_user

        try:
            if data == 'noop::page':
                return

            if data == 'joincheck::verify':
                joined = await is_user_joined_required_channels(context.bot, user.id if user else 0)
                if joined:
                    if self._is_group_chat(update):
                        await query.message.reply_text(
                            get_unlocked_welcome_text(user.first_name if user else ''),
                            parse_mode=ParseMode.HTML,
                        )
                    else:
                        await query.edit_message_text(get_unlocked_welcome_text(user.first_name if user else ''), parse_mode=ParseMode.HTML, reply_markup=home_keyboard())
                else:
                    await query.message.reply_text(
                        '❌ Abhi bhi required Telegram channels joined nahi mile.\n\nPehle sab required channels join karo, phir dobara check karo.',
                        reply_markup=locked_access_keyboard(),
                    )
                return

            if data == 'home::main':
                await query.edit_message_text('🏠 <b>Home</b>\nNeeche options use karo.', parse_mode=ParseMode.HTML, reply_markup=home_keyboard())
                return

            if data == 'home::categories':
                if not await self.ensure_access(update, context):
                    return
                await query.edit_message_text('📚 <b>Categories</b>', parse_mode=ParseMode.HTML, reply_markup=categories_keyboard(self.db.get_categories(), page=0))
                return

            if data == 'home::help':
                if not await self.ensure_access(update, context):
                    return
                await query.edit_message_text(self._help_text(bool(user and is_admin(user.id))), parse_mode=ParseMode.HTML, reply_markup=home_keyboard())
                return

            if data.startswith('page::'):
                if not await self.ensure_access(update, context):
                    return
                _, scope, value, page_text = data.split('::', 3)
                page = int(page_text)
                if scope == 'search':
                    await self.send_search_page_callback(query, user, value, page)
                elif scope == 'category':
                    await self.send_category_page(query, value, page)
                elif scope == 'featured':
                    total = self.db.count_featured_courses()
                    results = self.db.get_featured_courses(limit=PAGE_SIZE, offset=page * PAGE_SIZE)
                    await query.edit_message_text(
                        f'⭐ <b>Featured Courses</b>\nTotal: {total}',
                        parse_mode=ParseMode.HTML,
                        reply_markup=search_results_keyboard(results, 'featured', 'all', page, total),
                    )
                elif scope == 'cats':
                    await query.edit_message_text('📚 <b>Categories</b>', parse_mode=ParseMode.HTML, reply_markup=categories_keyboard(self.db.get_categories(), page=page))
                return

            if data.startswith('course::'):
                if not await self.ensure_access(update, context):
                    return
                course_id = int(data.split('::', 1)[1])
                course = self.db.get_course(course_id)
                if not course or not course.get('is_active', True):
                    await query.message.reply_text('❌ Course not found in database.')
                    return
                self.db.log_click(user.id if user else None, user.username if user and user.username else '', course_id, 'open_course')
                await self.send_course_card(query.message.reply_text, query.message.reply_photo, course)
                return

            if data.startswith('cat::'):
                if not await self.ensure_access(update, context):
                    return
                _, category, page_text = data.split('::', 2)
                await self.send_category_page(query, category, int(page_text))
                return

            if data.startswith('suggest::'):
                if not await self.ensure_access(update, context):
                    return
                _, keyword, page_text = data.split('::', 2)
                await self.send_search_page_callback(query, user, keyword, int(page_text))
                return

            if data.startswith('premium::'):
                if not await self.ensure_access(update, context):
                    return
                course_id = int(data.split('::', 1)[1])
                course = self.db.get_course(course_id)
                if not course:
                    await query.message.reply_text('❌ Course not found.')
                    return
                link = course.get('premium_channel_link') or PREMIUM_CHANNEL_LINK or 'Not configured'
                await query.message.reply_text(
                    f'🔓 Premium access manual approval based hai.\n\nCourse: {course["title"]}\nPurchase ke baad admin se contact karo.\nApproved hone ke baad premium link diya jayega:\n{link}'
                )
                return

            if data.startswith('premiumreq::'):
                if not await self.ensure_access(update, context):
                    return
                course_id = int(data.split('::', 1)[1])
                course = self.db.get_course(course_id)
                if not course:
                    await query.message.reply_text('❌ Course not found.')
                    return
                if not user:
                    await query.message.reply_text('❌ User not found.')
                    return
                _, status = self.db.add_purchase(user.id, user.username or '', course_id)
                if status == 'approved':
                    await query.message.reply_text('✅ Aapka access already approved hai. Inbox check karo.')
                elif status == 'pending':
                    await query.message.reply_text('⏳ Aapki request already pending hai. Admin approve karenge to DM aa jayega.')
                else:
                    await query.message.reply_text('✅ Payment request create ho gayi hai. Admin verify karke access denge.')
                    await self.notify_admins_pending_purchase(context, course, user)
                return

            if data.startswith('save::'):
                if not await self.ensure_access(update, context):
                    return
                if not user:
                    await query.message.reply_text('❌ User not found.')
                    return
                course_id = int(data.split('::', 1)[1])
                course = self.db.get_course(course_id)
                if not course:
                    await query.message.reply_text('❌ Course not found.')
                    return
                created = self.db.save_course(user.id, course_id)
                if created:
                    self.db.log_click(user.id, user.username or '', course_id, 'save_course')
                    await query.message.reply_text('⭐ Course saved successfully. /saved use karke list dekho.')
                else:
                    await query.message.reply_text('⭐ Ye course pehle se saved hai. /saved use karo.')
                return

            if data == 'featured::all::0' or data == 'featured::all':
                if not await self.ensure_access(update, context):
                    return
                total = self.db.count_featured_courses()
                results = self.db.get_featured_courses(limit=PAGE_SIZE, offset=0)
                if not results:
                    await query.message.reply_text('❌ No featured courses found.')
                    return
                await query.edit_message_text(
                    f'⭐ <b>Featured Courses</b>\nTotal: {total}',
                    parse_mode=ParseMode.HTML,
                    reply_markup=search_results_keyboard(results, 'featured', 'all', 0, total),
                )
                return

        except Exception:
            logger.exception('BUTTON_HANDLER_ERROR')
            await query.message.reply_text('❌ Button action failed. Please try again.')

    async def inline_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user:
            self.db.upsert_user(user_id=user.id, username=user.username or '', first_name=user.first_name or '', last_name=user.last_name or '')
        if not update.inline_query:
            return
        joined = await is_user_joined_required_channels(context.bot, user.id) if user else False
        if not joined:
            await update.inline_query.answer([], cache_time=1, switch_pm_text='Join required channels first', switch_pm_parameter='start')
            return
        query = update.inline_query.query.strip()
        if not query:
            await update.inline_query.answer([], cache_time=1)
            return

        results = self.db.search_courses(query, limit=20)
        inline_results = []
        for course in results:
            desc = f"{course.get('category') or 'General'} | {course.get('instructor') or 'Unknown'}"
            inline_results.append(
                InlineQueryResultArticle(
                    id=str(course['id']),
                    title=course['title'],
                    description=desc,
                    input_message_content=InputTextMessageContent(message_text=format_inline_course_message(course), parse_mode=ParseMode.HTML),
                )
            )
        await update.inline_query.answer(inline_results, cache_time=1)

    def _parse_admin_fields(self, text: str, command_name: str) -> dict[str, str]:
        payload = text.replace(command_name, '', 1).strip()
        fields: dict[str, str] = {}
        for line in payload.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                fields[key.strip().lower()] = value.strip()
        return fields

    async def addcourse(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        user = update.effective_user
        if not user or not is_admin(user.id):
            if update.message:
                await update.message.reply_text('❌ Admin only command.')
            return
        if not update.message or not update.message.text:
            return

        fields = self._parse_admin_fields(update.message.text, '/addcourse')
        required = ['title', 'instructor', 'category', 'description']
        for r in required:
            if not fields.get(r):
                await update.message.reply_text(f'❌ Missing field: {r}')
                return

        keywords = [k.strip() for k in fields.get('keywords', '').split(',') if k.strip()]
        course_id, created = self.db.add_course(
            title=fields.get('title', ''),
            instructor=fields.get('instructor', ''),
            category=fields.get('category', ''),
            description=fields.get('description', ''),
            thumbnail=fields.get('thumbnail', ''),
            download_url=fields.get('download', ''),
            how_to_download_url=fields.get('howtodownload', ''),
            demo_url=fields.get('demo', ''),
            contact_url=fields.get('contact', ''),
            premium_channel_link=fields.get('premiumlink', ''),
            is_featured=fields.get('featured', '0').strip() == '1',
            is_paid=fields.get('paid', '0').strip() == '1',
            price=fields.get('price', ''),
            keywords=keywords,
        )
        if not created:
            await update.message.reply_text(f'⚠️ Duplicate course already exists. Existing Course ID: {course_id}')
            return
        await update.message.reply_text(
            f'✅ Course Added Successfully\n\n📚 Title: {fields.get("title")}\n🧑‍🏫 Instructor: {fields.get("instructor")}\n📁 Category: {fields.get("category")}\n🆔 Course ID: {course_id}\n\nThumbnail add karne ke liye is message ke reply me photo bhejo ya /setthumb {course_id} use karo.'
        )

    async def updatecourse(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        user = update.effective_user
        if not user or not is_admin(user.id):
            if update.message:
                await update.message.reply_text('❌ Admin only command.')
            return
        if not update.message or not update.message.text:
            return

        payload = update.message.text.replace('/updatecourse', '', 1).strip()
        if not payload:
            await update.message.reply_text('Usage:\n/updatecourse 12\ntitle: New Title\nprice: 499')
            return

        lines = [line for line in payload.split('\n') if line.strip()]
        if not lines or not lines[0].strip().isdigit():
            await update.message.reply_text('Usage:\n/updatecourse 12\ntitle: New Title\nprice: 499')
            return

        course_id = int(lines[0].strip())
        course = self.db.get_course(course_id)
        if not course:
            await update.message.reply_text('❌ Course not found.')
            return

        fields: dict[str, str] = {}
        for line in lines[1:]:
            if ':' in line:
                key, value = line.split(':', 1)
                fields[key.strip().lower()] = value.strip()

        mapped: dict[str, object] = {}
        keymap = {
            'title': 'title', 'instructor': 'instructor', 'category': 'category', 'description': 'description',
            'thumbnail': 'thumbnail', 'download': 'download_url', 'howtodownload': 'how_to_download_url',
            'demo': 'demo_url', 'contact': 'contact_url', 'premiumlink': 'premium_channel_link',
            'price': 'price', 'active': 'is_active', 'featured': 'is_featured', 'paid': 'is_paid'
        }
        for k, v in fields.items():
            if k == 'keywords':
                continue
            mapped_key = keymap.get(k)
            if not mapped_key:
                continue
            if mapped_key in {'is_active', 'is_featured', 'is_paid'}:
                mapped[mapped_key] = v.strip().lower() in ('1', 'true', 'yes', 'on')
            else:
                mapped[mapped_key] = v

        keywords = None
        if 'keywords' in fields:
            keywords = [k.strip() for k in fields['keywords'].split(',') if k.strip()]

        changed = self.db.update_course_fields(course_id, mapped, keywords)
        if not changed:
            await update.message.reply_text('❌ Koi valid field nahi mili.')
            return
        await update.message.reply_text(f'✅ Course updated successfully. Course ID: {course_id}')

    async def save_thumbnail(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        user = update.effective_user
        if not user or not is_admin(user.id):
            if update.message:
                await update.message.reply_text('❌ Admin only command.')
            return
        if not update.message or not update.message.photo:
            return

        course_id = context.user_data.get('awaiting_thumbnail_course_id')
        if not course_id and update.message.reply_to_message and update.message.reply_to_message.text:
            replied_text = update.message.reply_to_message.text or ''
            for line in replied_text.split('\n'):
                if 'Course ID:' in line:
                    try:
                        course_id = int(line.split('Course ID:')[1].strip())
                    except Exception:
                        course_id = None
                    break
                if '🆔 Course ID:' in line:
                    try:
                        course_id = int(line.split('🆔 Course ID:')[1].strip())
                    except Exception:
                        course_id = None
                    break

        if not course_id:
            return
        course = self.db.get_course(course_id)
        if not course:
            await update.message.reply_text('❌ Course not found.')
            return

        file_id = update.message.photo[-1].file_id
        self.db.update_course_thumbnail(course_id, file_id)
        context.user_data.pop('awaiting_thumbnail_course_id', None)
        await update.message.reply_text(f'✅ Thumbnail saved successfully for course ID: {course_id}')

    async def setthumb(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        user = update.effective_user
        if not user or not is_admin(user.id):
            if update.message:
                await update.message.reply_text('❌ Admin only command.')
            return
        if not update.message:
            return
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text('Usage: /setthumb 12')
            return
        course_id = int(context.args[0])
        course = self.db.get_course(course_id)
        if not course:
            await update.message.reply_text('❌ Course not found.')
            return
        context.user_data['awaiting_thumbnail_course_id'] = course_id
        await update.message.reply_text(f'📸 Ab course ID {course_id} ke liye photo bhejo.')

    async def importcsv(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        user = update.effective_user
        if not user or not is_admin(user.id):
            if update.message:
                await update.message.reply_text('❌ Admin only command.')
            return
        if not update.message:
            return
        if not context.args:
            await update.message.reply_text('Usage:\n/importcsv sample_courses.csv\nYa direct CSV file upload karo.')
            return
        csv_path = ' '.join(context.args).strip()
        try:
            imported, skipped = import_courses_from_csv(self.db, csv_path)
            await update.message.reply_text(f'✅ CSV import complete. Imported: {imported} | Skipped duplicates: {skipped}')
        except Exception as e:
            await update.message.reply_text(f'❌ CSV import failed:\n{e}')

    async def importcsv_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        user = update.effective_user
        if not user or not is_admin(user.id):
            return
        if not update.message or not update.message.document:
            return
        doc = update.message.document
        if not (doc.file_name or '').lower().endswith('.csv'):
            return
        temp_path = Path('/tmp') / doc.file_name
        tg_file = await context.bot.get_file(doc.file_id)
        await tg_file.download_to_drive(custom_path=str(temp_path))
        try:
            imported, skipped = import_courses_from_csv(self.db, str(temp_path))
            await update.message.reply_text(f'✅ CSV upload import complete. Imported: {imported} | Skipped duplicates: {skipped}')
        except Exception as e:
            await update.message.reply_text(f'❌ CSV upload import failed:\n{e}')
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass

    async def deletecourse(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        user = update.effective_user
        if not user or not is_admin(user.id):
            if update.message:
                await update.message.reply_text('❌ Admin only command.')
            return
        if not update.message or not update.message.text:
            return
        text = update.message.text.replace('/deletecourse', '', 1).strip()
        if not text.isdigit():
            await update.message.reply_text('Usage: /deletecourse 3')
            return
        course_id = int(text)
        self.db.soft_delete_course(course_id)
        await update.message.reply_text('🗑 Course soft deleted.')

    async def restorecourse(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        user = update.effective_user
        if not user or not is_admin(user.id):
            if update.message:
                await update.message.reply_text('❌ Admin only command.')
            return
        if not update.message or not update.message.text:
            return
        text = update.message.text.replace('/restorecourse', '', 1).strip()
        if not text.isdigit():
            await update.message.reply_text('Usage: /restorecourse 3')
            return
        course_id = int(text)
        self.db.restore_course(course_id)
        await update.message.reply_text('♻️ Course restored successfully.')

    async def listcourses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        user = update.effective_user
        if not user or not is_admin(user.id):
            if update.message:
                await update.message.reply_text('❌ Admin only command.')
            return
        if not update.message:
            return
        courses = self.db.list_courses(limit=100, active_only=False)
        if not courses:
            await update.message.reply_text('No courses found.')
            return
        lines = ['📚 <b>Courses</b>']
        for c in courses:
            lines.append(f"{c['id']}. {escape_html(c['title'])} | Paid: {c['is_paid']} | Featured: {c['is_featured']} | Active: {c.get('is_active', True)}")
        text = '\n'.join(lines)
        if len(text) > 3800:
            text = text[:3800] + '\n...'
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)

    async def feature(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        user = update.effective_user
        if not user or not is_admin(user.id):
            if update.message:
                await update.message.reply_text('❌ Admin only command.')
            return
        if not update.message or not update.message.text:
            return
        text = update.message.text.replace('/feature', '', 1).strip()
        if not text.isdigit():
            await update.message.reply_text('Usage: /feature 2')
            return
        self.db.set_featured(int(text), True)
        await update.message.reply_text('⭐ Featured enabled.')

    async def unfeature(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        user = update.effective_user
        if not user or not is_admin(user.id):
            if update.message:
                await update.message.reply_text('❌ Admin only command.')
            return
        if not update.message or not update.message.text:
            return
        text = update.message.text.replace('/unfeature', '', 1).strip()
        if not text.isdigit():
            await update.message.reply_text('Usage: /unfeature 2')
            return
        self.db.set_featured(int(text), False)
        await update.message.reply_text('✅ Featured removed.')


    async def requests_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        user = update.effective_user
        if not user or not is_admin(user.id):
            if update.message:
                await update.message.reply_text('❌ Admin only command.')
            return
        if not update.message:
            return
        rows = self.db.get_pending_requests(limit=25)
        if not rows:
            await update.message.reply_text('✅ No pending course requests.')
            return
        lines = ['📥 <b>Pending Course Requests</b>']
        for row in rows:
            uname = f"@{row['username']}" if row.get('username') else '-'
            lines.append(f"\nID: <code>{row['id']}</code>\nUser ID: <code>{row['user_id']}</code>\nUsername: {uname}\nRequest: {escape_html(row['request_text'])}\nDone: <code>/requestdone {row['id']}</code>")
        text = '\n'.join(lines)
        if len(text) > 3800:
            text = text[:3800] + '\n...'
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)

    async def requestdone_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        user = update.effective_user
        if not user or not is_admin(user.id):
            if update.message:
                await update.message.reply_text('❌ Admin only command.')
            return
        if not update.message:
            return
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text('Usage: /requestdone request_id')
            return
        request_id = int(context.args[0])
        changed = self.db.complete_request(request_id, user.id)
        if not changed:
            await update.message.reply_text('❌ Pending request not found.')
            return
        await update.message.reply_text('✅ Request marked as completed.')

    async def broadcast_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        user = update.effective_user
        if not user or not is_admin(user.id):
            if update.message:
                await update.message.reply_text('❌ Admin only command.')
            return
        if not update.message or not update.message.text:
            return
        payload = update.message.text.replace('/broadcast', '', 1).strip()
        if not payload:
            await update.message.reply_text('Usage: /broadcast your message')
            return
        user_ids = self.db.get_all_user_ids()
        sent = 0
        failed = 0
        for uid in user_ids:
            try:
                await context.bot.send_message(chat_id=uid, text=payload)
                sent += 1
            except Exception:
                failed += 1
        await update.message.reply_text(f'📢 Broadcast complete. Sent: {sent} | Failed: {failed}')

    async def maintenance_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        user = update.effective_user
        if not user or not is_admin(user.id):
            if update.message:
                await update.message.reply_text('❌ Admin only command.')
            return
        if not update.message:
            return
        if not context.args:
            status = self.db.get_maintenance_status()
            await update.message.reply_text(f"Maintenance: {'ON' if status['enabled'] else 'OFF'}\\nMessage: {status['message']}")
            return
        action = context.args[0].lower()
        if action == 'off':
            self.db.set_maintenance(False)
            await update.message.reply_text('✅ Maintenance mode disabled.')
            return
        if action == 'on':
            message = ' '.join(context.args[1:]).strip() or 'Bot upgrade chal raha hai. Thodi der baad try karo.'
            self.db.set_maintenance(True, message)
            await update.message.reply_text('✅ Maintenance mode enabled.')
            return
        await update.message.reply_text('Usage:\n/maintenance on reason\n/maintenance off')

    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        user = update.effective_user
        if not user or not is_admin(user.id):
            if update.message:
                await update.message.reply_text('❌ Admin only command.')
            return
        if not update.message:
            return
        s = self.db.get_stats()
        lines = [
            '📊 <b>Analytics Dashboard</b>',
            f"Total Courses: {s['total_courses']}",
            f"Paid Courses: {s['total_paid_courses']}",
            f"Total Searches: {s['total_searches']}",
            f"Total Users: {s['total_users']}",
            f"24h Active Users: {s['active_24h']}",
            f"7d Active Users: {s['active_7d']}",
            f"Pending Purchases: {s['pending_purchases']}",
            '',
            '📁 Top Categories:',
        ]
        for row in s['top_categories']:
            lines.append(f"• {row['category']} — {row['c']}")
        lines.append('')
        lines.append('🔥 Top Queries:')
        for row in s['popular_queries']:
            lines.append(f"• {row['query']} — {row['c']}")
        lines.append('')
        lines.append('🚫 Zero Result Queries:')
        for row in s['zero_results']:
            lines.append(f"• {row['query']} — {row['c']}")
        lines.append('')
        lines.append('📈 Top Clicked Courses:')
        for row in s['top_clicked']:
            lines.append(f"• {row['title']} — {row['ccount']}")
        text = '\n'.join(lines)
        if len(text) > 3800:
            text = text[:3800] + '\n...'
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)

    async def pendingpayments(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        user = update.effective_user
        if not user or not is_admin(user.id):
            if update.message:
                await update.message.reply_text('❌ Admin only command.')
            return
        if not update.message:
            return
        rows = self.db.get_pending_purchases(limit=25)
        if not rows:
            await update.message.reply_text('✅ No pending payment requests.')
            return
        lines = ['🧾 <b>Pending Payment Requests</b>']
        for row in rows:
            uname = f"@{row['username']}" if row.get('username') else '-'
            lines.append(
                f"\nUser ID: <code>{row['user_id']}</code>\nUsername: {uname}\nCourse ID: {row['course_id']}\nCourse: {escape_html(row['course_title'])}\nGrant: <code>/grant {row['user_id']} {row['course_id']}</code>"
            )
        text = '\n'.join(lines)
        if len(text) > 3800:
            text = text[:3800] + '\n...'
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)

    async def grant(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.track_user(update)
        user = update.effective_user
        if not user or not is_admin(user.id):
            if update.message:
                await update.message.reply_text('❌ Admin only command.')
            return
        if not update.message:
            return
        args = context.args
        if len(args) < 2:
            await update.message.reply_text('Usage: /grant user_id course_id')
            return
        try:
            target_user_id = int(args[0])
            course_id = int(args[1])
        except ValueError:
            await update.message.reply_text('❌ Invalid user_id or course_id.')
            return
        course = self.db.get_course(course_id)
        if not course:
            await update.message.reply_text('Course not found.')
            return

        self.db.approve_purchase(target_user_id, course_id, user.id)
        premium_link = course.get('premium_channel_link') or PREMIUM_CHANNEL_LINK
        if premium_link:
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f'🎉 Aapka premium access approve ho gaya hai.\n\nCourse: {course["title"]}\nJoin here: {premium_link}',
                )
                await update.message.reply_text('✅ Access granted and user notified.')
            except Exception as e:
                await update.message.reply_text(f'Approved but DM nahi gaya: {e}')
        else:
            await update.message.reply_text('Approved, but premium link not configured.')
