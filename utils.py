from config import ADMIN_IDS


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def format_course_caption(course: dict) -> str:
    title = course.get("title", "Untitled Course")
    instructor = course.get("instructor") or "Unknown"
    category = course.get("category") or "General"
    description = course.get("description") or "No description added."

    return (
        f"📚 <b>{title}</b>\n\n"
        f"👨‍🏫 <b>Instructor:</b> {instructor}\n"
        f"🗂 <b>Category:</b> {category}\n"
        f"📝 <b>About:</b> {description}\n\n"
        f"👇 Neeche button se course access karo."
    )