from __future__ import annotations

from difflib import get_close_matches
import html
from typing import Iterable

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import (
    ADMIN_IDS,
    BOT_NAME,
    FORCE_SUB_CHANNELS,
    FORCE_SUB_CHANNEL_URLS,
    WHATSAPP_CHANNEL_URL,
)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def normalize_text(text: str | None) -> str:
    return ' '.join((text or '').strip().lower().split())


def unique_keep_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = normalize_text(item)
        if key and key not in seen:
            seen.add(key)
            result.append(item.strip())
    return result


def suggest_keyword(query: str, all_keywords: list[str]) -> list[str]:
    cleaned = normalize_text(query)
    if not cleaned:
        return []

    close = get_close_matches(cleaned, [normalize_text(x) for x in all_keywords], n=8, cutoff=0.5)
    partial = [kw for kw in all_keywords if cleaned in normalize_text(kw)][:8]
    starts = [kw for kw in all_keywords if normalize_text(kw).startswith(cleaned)][:8]
    return unique_keep_order(starts + partial + close + all_keywords[:0])


def escape_html(text: str | None) -> str:
    return html.escape(text or '')


async def is_user_joined_required_channels(bot, user_id: int) -> bool:
    if not FORCE_SUB_CHANNELS:
        return True

    for channel in FORCE_SUB_CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            status = getattr(member, 'status', '')
            if status in ('left', 'kicked'):
                return False
        except Exception:
            return False
    return True


def build_force_sub_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for idx, url in enumerate(FORCE_SUB_CHANNEL_URLS[:5], start=1):
        rows.append([InlineKeyboardButton(f'📢 Join Channel {idx}', url=url)])

    if WHATSAPP_CHANNEL_URL:
        rows.append([InlineKeyboardButton('💬 Join WhatsApp Channel', url=WHATSAPP_CHANNEL_URL)])

    rows.append([InlineKeyboardButton('✅ I Joined', callback_data='joincheck::verify')])
    rows.append([InlineKeyboardButton('🔄 Check Again', callback_data='joincheck::verify')])
    return InlineKeyboardMarkup(rows)


def build_home_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton('📚 Categories', callback_data='home::categories')],
        [InlineKeyboardButton('⭐ Featured Courses', callback_data='featured::all::0')],
        [InlineKeyboardButton('ℹ️ Help', callback_data='home::help')],
    ]
    return InlineKeyboardMarkup(rows)


def get_locked_welcome_text(user_first_name: str = '') -> str:
    user_line = f'👋 Hello <b>{escape_html(user_first_name)}</b>\n\n' if user_first_name else ''
    return (
        f'{user_line}'
        f'🚀 <b>Welcome to {escape_html(BOT_NAME)}</b>\n\n'
        'Yahaan aap premium aur free courses search kar sakte ho.\n'
        'Lekin bot use karne se pehle required Telegram channels join karna zaroori hai.\n\n'
        '🔐 <b>Access Locked</b>\n'
        'Pehle niche diye gaye channels join karo.\n'
        'Uske baad <b>✅ I Joined</b> button dabao.\n\n'
        'Join hone ke baad hi aap:\n'
        '• Course search kar paoge\n'
        '• Categories dekh paoge\n'
        '• Featured courses open kar paoge\n'
        '• Download buttons access kar paoge'
    )


def get_unlocked_welcome_text(user_first_name: str = '') -> str:
    user_line = f'👋 Hello <b>{escape_html(user_first_name)}</b>\n\n' if user_first_name else ''
    return (
        f'{user_line}'
        f'🎉 <b>Welcome to {escape_html(BOT_NAME)}</b>\n\n'
        '✅ Access unlocked successfully.\n\n'
        'Ab aap bot use kar sakte ho.\n\n'
        'Search karne ke examples:\n'
        '• /search python\n'
        '• /search flutter\n'
        '• harkirat\n'
        '• dsa\n\n'
        'Ya direct course ka naam type karo.'
    )


def get_locked_reply_text() -> str:
    return (
        '🔒 Bot use karne ke liye pehle required Telegram channels join karo.\n\n'
        'Join karne ke baad <b>✅ I Joined</b> button dabao.'
    )


def format_course_caption(course: dict) -> str:
    title = escape_html(course.get('title', 'Untitled Course'))
    instructor = escape_html(course.get('instructor') or 'Unknown')
    category = escape_html(course.get('category') or 'General')
    description = escape_html(course.get('description') or 'No description available.')
    is_paid = bool(course.get('is_paid'))
    price = escape_html(course.get('price') or '')
    is_featured = bool(course.get('is_featured'))

    lines = [
        f'📚 <b>{title}</b>',
        '',
        f'👨‍🏫 <b>Instructor:</b> {instructor}',
        f'🗂 <b>Category:</b> {category}',
        f'📝 <b>About:</b> {description}',
    ]

    if is_featured:
        lines.append('⭐ <b>Featured:</b> Yes')

    if is_paid:
        lines.append(f'💰 <b>Price:</b> {price or "Contact Admin"}')
        lines.append('🔒 <b>Type:</b> Paid Course')
    else:
        lines.append('🆓 <b>Type:</b> Free Course')

    lines.append('')
    lines.append('👇 Neeche button se course access karo.')
    return '\n'.join(lines)


def format_inline_course_message(course: dict) -> str:
    title = escape_html(course.get('title', 'Untitled Course'))
    instructor = escape_html(course.get('instructor') or 'Unknown')
    category = escape_html(course.get('category') or 'General')
    course_id = course.get('id')
    return (
        f'📚 <b>{title}</b>\n'
        f'👨‍🏫 <b>Instructor:</b> {instructor}\n'
        f'🗂 <b>Category:</b> {category}\n'
        f'🆔 <b>Course ID:</b> {course_id}\n\n'
        'Full card open karne ke liye bot me course search karo.'
    )
