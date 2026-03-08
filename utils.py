from difflib import get_close_matches
from config import ADMIN_IDS


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def suggest_keyword(query: str, all_keywords: list[str]) -> list[str]:
    return get_close_matches(query.strip().lower(), all_keywords, n=5, cutoff=0.5)


def format_course_caption(course: dict) -> str:
    title = course.get("title", "Untitled Course")
    instructor = course.get("instructor") or "Unknown"
    category = course.get("category") or "General"
    description = course.get("description") or "No description available."
    is_paid = bool(course.get("is_paid"))
    price = course.get("price") or ""

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

    lines.append("")
    lines.append("👇 Neeche button se course access karo.")
    return "\n".join(lines)