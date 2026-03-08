import csv
from db import Database


def import_courses_from_csv(db: Database, csv_path: str) -> int:
    count = 0

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            keywords = [k.strip() for k in row.get("keywords", "").split(",") if k.strip()]

            db.add_course(
                title=row.get("title", "").strip(),
                instructor=row.get("instructor", "").strip(),
                category=row.get("category", "").strip(),
                description=row.get("description", "").strip(),
                thumbnail=row.get("thumbnail", "").strip(),
                download_url=row.get("download_url", "").strip(),
                how_to_download_url=row.get("how_to_download_url", "").strip(),
                demo_url=row.get("demo_url", "").strip(),
                contact_url=row.get("contact_url", "").strip(),
                premium_channel_link=row.get("premium_channel_link", "").strip(),
                is_featured=str(row.get("is_featured", "0")).strip() in ("1", "true", "True"),
                is_paid=str(row.get("is_paid", "0")).strip() in ("1", "true", "True"),
                price=row.get("price", "").strip(),
                keywords=keywords,
            )
            count += 1

    return count