from __future__ import annotations

from difflib import get_close_matches
import html

from config import ADMIN_IDS


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def suggest_keyword(query: str, all_keywords: list[str]) -> list[str]:
    cleaned = query.strip().lower()
    if not cleaned:
        return []
    return get_close_matches(cleaned, all_keywords, n=5, cutoff=0.5)


def escape_html(text: str | None) -> str:
    return html.escape(text or "")


def format_course_caption(course: dict) -> str:
    title = escape_html(course.get("title", "Untitled Course"))
    instructor = escape_html(course.get("instructor") or "Unknown")
    category = escape_html(course.get("category") or "General")
    description = escape_html(course.get("description") or "No description available.")
    is_paid = bool(course.get("is_paid"))
    price = escape_html(course.get("price") or "")
    is_featured = bool(course.get("is_featured"))

    lines = [
        f"📚 <b>{title}</b>",
        "",
        f"👨‍🏫 <b>Instructor:</b> {instructor}",
        f"🗂 <b>Category:</b> {category}",
        f"📝 <b>About:</b> {description}",
    ]

    if is_featured:
        lines.append("⭐ <b>Featured:</b> Yes")

    if is_paid:
        lines.append(f"💰 <b>Price:</b> {price or 'Contact Admin'}")
        lines.append("🔒 <b>Type:</b> Paid Course")
    else:
        lines.append("🆓 <b>Type:</b> Free Course")

    lines.append("")
    lines.append("👇 Neeche button se course access karo.")
    return "\n".join(lines)


def format_course_text(course: dict) -> str:
    title = escape_html(course.get("title", "Untitled Course"))
    instructor = escape_html(course.get("instructor") or "Unknown")
    category = escape_html(course.get("category") or "General")
    description = escape_html(course.get("description") or "No description available.")
    download_url = escape_html(course.get("download_url") or "")
    how_to_download_url = escape_html(course.get("how_to_download_url") or "")
    demo_url = escape_html(course.get("demo_url") or "")
    contact_url = escape_html(course.get("contact_url") or "")
    premium_channel_link = escape_html(course.get("premium_channel_link") or "")
    is_paid = bool(course.get("is_paid"))
    price = escape_html(course.get("price") or "")

    lines = [
        f"📚 <b>{title}</b>",
        "",
        f"👨‍🏫 <b>Instructor:</b> {instructor}",
        f"🗂 <b>Category:</b> {category}",
        f"📝 <b>About:</b> {description}",
    ]

    if is_paid:
        lines.append(f"💰 <b>Price:</b> {price or 'Contact Admin'}")
        lines.append("🔒 <b>Type:</b> Paid Course")
    else:
        lines.append("🆓 <b>Type:</b> Free Course")

    if download_url:
        lines.extend(["", f"🔗 <b>Download:</b> {download_url}"])
    if how_to_download_url:
        lines.append(f"📥 <b>How To Download:</b> {how_to_download_url}")
    if demo_url:
        lines.append(f"🎬 <b>Demo:</b> {demo_url}")
    if contact_url:
        lines.append(f"🛟 <b>Support:</b> {contact_url}")
    if premium_channel_link:
        lines.append(f"💎 <b>Premium:</b> {premium_channel_link}")

    return "\n".join(lines)