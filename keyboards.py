from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import MAIN_CHANNEL_URL, PLAYLISTS_URL, SUPPORT_CONTACT_URL


def course_keyboard(course: dict) -> InlineKeyboardMarkup:
    rows = []

    if course.get("is_paid"):
        contact_url = course.get("contact_url") or SUPPORT_CONTACT_URL
        rows.append([InlineKeyboardButton("💳 Buy Now", url=contact_url)])

        if course.get("demo_url"):
            rows.append([InlineKeyboardButton("🎬 Demo", url=course["demo_url"])])

        rows.append([InlineKeyboardButton("💬 Chat to Buy", url=contact_url)])

        if course.get("premium_channel_link"):
            rows.append([
                InlineKeyboardButton(
                    "🔓 Premium Access Info",
                    callback_data=f"premium::{course['id']}"
                )
            ])
    else:
        if course.get("download_url"):
            rows.append([InlineKeyboardButton("📥 Download Course", url=course["download_url"])])

        if course.get("how_to_download_url"):
            rows.append([InlineKeyboardButton("📺 How to Download", url=course["how_to_download_url"])])

        if course.get("demo_url"):
            rows.append([InlineKeyboardButton("🎬 Demo", url=course["demo_url"])])

    rows.append([InlineKeyboardButton("📢 Join Our Main Channel", url=MAIN_CHANNEL_URL)])
    rows.append([InlineKeyboardButton("📂 Join PlayLists", url=PLAYLISTS_URL)])

    return InlineKeyboardMarkup(rows)


def categories_keyboard(categories: list[str]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(cat, callback_data=f"cat::{cat}")] for cat in categories]
    rows.append([InlineKeyboardButton("⭐ Featured Courses", callback_data="featured::all")])
    return InlineKeyboardMarkup(rows)


def search_results_keyboard(results: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for course in results:
        title = course["title"]
        if len(title) > 55:
            title = title[:52] + "..."
        rows.append([InlineKeyboardButton(title, callback_data=f"course::{course['id']}")])
    return InlineKeyboardMarkup(rows)


def suggestions_keyboard(suggestions: list[str]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(s, callback_data=f"suggest::{s}")] for s in suggestions]
    return InlineKeyboardMarkup(rows)