from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import MAIN_CHANNEL_URL, PAGE_SIZE, PLAYLISTS_URL, SUPPORT_CONTACT_URL
from utils import build_force_sub_keyboard, build_home_keyboard


def _truncate(title: str, limit: int = 55) -> str:
    return title if len(title) <= limit else title[: limit - 3] + '...'


def build_pagination_rows(scope: str, value: str, page: int, total: int) -> list[list[InlineKeyboardButton]]:
    rows: list[list[InlineKeyboardButton]] = []
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    nav: list[InlineKeyboardButton] = []

    if page > 0:
        nav.append(InlineKeyboardButton('⏮ Prev', callback_data=f'page::{scope}::{value}::{page - 1}'))
    nav.append(InlineKeyboardButton(f'📄 {page + 1}/{total_pages}', callback_data='noop::page'))
    if page + 1 < total_pages:
        nav.append(InlineKeyboardButton('Next ⏭', callback_data=f'page::{scope}::{value}::{page + 1}'))

    if nav:
        rows.append(nav)
    return rows


def course_keyboard(course: dict) -> InlineKeyboardMarkup:
    rows = []

    if course.get('is_paid'):
        contact_url = course.get('contact_url') or SUPPORT_CONTACT_URL
        if contact_url:
            rows.append([InlineKeyboardButton('💳 Buy Now', url=contact_url)])
            rows.append([InlineKeyboardButton('💬 Chat to Buy', url=contact_url)])

        rows.append([InlineKeyboardButton('🧾 I Have Paid', callback_data=f'premiumreq::{course["id"]}')])

        if course.get('demo_url'):
            rows.append([InlineKeyboardButton('🎬 Demo', url=course['demo_url'])])

        rows.append([InlineKeyboardButton('🔓 Premium Access Info', callback_data=f'premium::{course["id"]}')])
    else:
        if course.get('download_url'):
            rows.append([InlineKeyboardButton('📥 Download Course', url=course['download_url'])])
        if course.get('how_to_download_url'):
            rows.append([InlineKeyboardButton('📺 How to Download', url=course['how_to_download_url'])])
        if course.get('demo_url'):
            rows.append([InlineKeyboardButton('🎬 Demo', url=course['demo_url'])])

    rows.append([InlineKeyboardButton('⭐ Save Course', callback_data=f'save::{course["id"]}')])

    if MAIN_CHANNEL_URL:
        rows.append([InlineKeyboardButton('📢 Join Our Main Channel', url=MAIN_CHANNEL_URL)])
    if PLAYLISTS_URL:
        rows.append([InlineKeyboardButton('📂 Join PlayLists', url=PLAYLISTS_URL)])

    return InlineKeyboardMarkup(rows)


def categories_keyboard(categories: list[str], page: int = 0) -> InlineKeyboardMarkup:
    start = page * PAGE_SIZE
    current = categories[start : start + PAGE_SIZE]
    rows = [[InlineKeyboardButton(cat, callback_data=f'cat::{cat}::0')] for cat in current]
    rows.extend(build_pagination_rows('cats', 'all', page, len(categories)))
    rows.append([InlineKeyboardButton('⭐ Featured Courses', callback_data='featured::all::0')])
    rows.append([InlineKeyboardButton('🏠 Home', callback_data='home::main')])
    return InlineKeyboardMarkup(rows)


def search_results_keyboard(results: list[dict], scope: str, value: str, page: int, total: int) -> InlineKeyboardMarkup:
    rows = []
    for course in results:
        rows.append([InlineKeyboardButton(_truncate(course['title']), callback_data=f'course::{course["id"]}')])
    rows.extend(build_pagination_rows(scope, value, page, total))
    rows.append([InlineKeyboardButton('🏠 Home', callback_data='home::main')])
    return InlineKeyboardMarkup(rows)


def suggestions_keyboard(suggestions: list[str]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(s, callback_data=f'suggest::{s}::0')] for s in suggestions[:10]]
    rows.append([InlineKeyboardButton('🏠 Home', callback_data='home::main')])
    return InlineKeyboardMarkup(rows)


def locked_access_keyboard() -> InlineKeyboardMarkup:
    return build_force_sub_keyboard()


def home_keyboard() -> InlineKeyboardMarkup:
    return build_home_keyboard()
