from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import MAIN_CHANNEL_URL, PLAYLISTS_URL


def course_keyboard(course: dict) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("📥 Download Course", url=course["download_url"])],
    ]

    if course.get("how_to_download_url"):
        buttons.append(
            [InlineKeyboardButton("📺 How to Download", url=course["how_to_download_url"])]
        )

    buttons.append([InlineKeyboardButton("📢 Join Our Main Channel", url=MAIN_CHANNEL_URL)])
    buttons.append([InlineKeyboardButton("📂 Join PlayLists", url=PLAYLISTS_URL)])

    return InlineKeyboardMarkup(buttons)


def categories_keyboard(categories: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for cat in categories:
        rows.append([InlineKeyboardButton(cat, callback_data=f"cat::{cat}")])

    rows.append([InlineKeyboardButton("⭐ Featured Courses", callback_data="featured::all")])
    return InlineKeyboardMarkup(rows)


def search_results_keyboard(results: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for course in results:
        title = course["title"]
        if len(title) > 55:
            title = title[:52] + "..."
        rows.append([InlineKeyboardButton(title, callback_data=f"course::{course['id']}")])

    rows.append([InlineKeyboardButton("📢 Main Channel", url=MAIN_CHANNEL_URL)])
    return InlineKeyboardMarkup(rows)