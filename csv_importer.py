import csv
from pathlib import Path

from db import Database


def import_courses_from_csv(db: Database, csv_path: str) -> tuple[int, int]:
    imported = 0
    skipped = 0
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f'CSV file not found: {csv_path}')

    with path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            keywords = [k.strip() for k in (row.get('keywords') or '').split(',') if k.strip()]
            _, created = db.add_course(
                title=row.get('title', '').strip(),
                instructor=row.get('instructor', '').strip(),
                category=row.get('category', '').strip(),
                description=row.get('description', '').strip(),
                thumbnail=row.get('thumbnail', '').strip(),
                download_url=row.get('download_url', '').strip(),
                how_to_download_url=row.get('how_to_download_url', '').strip(),
                demo_url=row.get('demo_url', '').strip(),
                contact_url=row.get('contact_url', '').strip(),
                premium_channel_link=row.get('premium_channel_link', '').strip(),
                is_featured=str(row.get('is_featured', '0')).strip().lower() in ('1', 'true', 'yes'),
                is_paid=str(row.get('is_paid', '0')).strip().lower() in ('1', 'true', 'yes'),
                price=row.get('price', '').strip(),
                keywords=keywords,
            )
            if created:
                imported += 1
            else:
                skipped += 1

    return imported, skipped
