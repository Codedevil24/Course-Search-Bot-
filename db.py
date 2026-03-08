import sqlite3
from contextlib import closing
from difflib import SequenceMatcher
from typing import Any


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self):
        with closing(self.get_conn()) as conn:
            cur = conn.cursor()

            cur.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                instructor TEXT,
                category TEXT,
                description TEXT,
                thumbnail_url TEXT,
                download_url TEXT,
                how_to_download_url TEXT,
                demo_url TEXT,
                contact_url TEXT,
                premium_channel_link TEXT,
                is_featured INTEGER DEFAULT 0,
                is_paid INTEGER DEFAULT 0,
                price TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS course_keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                keyword TEXT NOT NULL,
                FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS search_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                query TEXT NOT NULL,
                matched_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS course_clicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                course_id INTEGER,
                action_type TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                course_id INTEGER,
                status TEXT DEFAULT 'pending',
                payment_note TEXT,
                approved_by INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                first_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """)

            conn.commit()

    def upsert_user(self, user_id: int, username: str = "", first_name: str = "", last_name: str = ""):
        with closing(self.get_conn()) as conn:
            conn.execute("""
                INSERT INTO users (user_id, username, first_name, last_name, first_seen_at, last_seen_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=excluded.username,
                    first_name=excluded.first_name,
                    last_name=excluded.last_name,
                    last_seen_at=CURRENT_TIMESTAMP
            """, (user_id, username, first_name, last_name))
            conn.commit()

    def add_course(
        self,
        title: str,
        instructor: str,
        category: str,
        description: str,
        thumbnail_url: str,
        download_url: str,
        how_to_download_url: str,
        demo_url: str,
        contact_url: str,
        premium_channel_link: str,
        is_featured: int,
        is_paid: int,
        price: str,
        keywords: list[str],
    ) -> int:
        with closing(self.get_conn()) as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO courses (
                    title, instructor, category, description, thumbnail_url,
                    download_url, how_to_download_url, demo_url, contact_url,
                    premium_channel_link, is_featured, is_paid, price
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                title, instructor, category, description, thumbnail_url,
                download_url, how_to_download_url, demo_url, contact_url,
                premium_channel_link, is_featured, is_paid, price
            ))
            course_id = cur.lastrowid

            for kw in keywords:
                kw = kw.strip().lower()
                if kw:
                    cur.execute(
                        "INSERT INTO course_keywords (course_id, keyword) VALUES (?, ?)",
                        (course_id, kw),
                    )

            conn.commit()
            return course_id

    def update_course_thumbnail(self, course_id: int, thumbnail_file_id: str):
        with closing(self.get_conn()) as conn:
            conn.execute("""
                UPDATE courses
                SET thumbnail_url=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (thumbnail_file_id, course_id))
            conn.commit()

    def delete_course(self, course_id: int):
        with closing(self.get_conn()) as conn:
            conn.execute("DELETE FROM courses WHERE id=?", (course_id,))
            conn.commit()

    def get_course(self, course_id: int) -> dict[str, Any] | None:
        with closing(self.get_conn()) as conn:
            row = conn.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
            return dict(row) if row else None

    def list_courses(self, limit: int = 100) -> list[dict[str, Any]]:
        with closing(self.get_conn()) as conn:
            rows = conn.execute("""
                SELECT * FROM courses
                ORDER BY updated_at DESC, created_at DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    def set_featured(self, course_id: int, value: int):
        with closing(self.get_conn()) as conn:
            conn.execute("""
                UPDATE courses
                SET is_featured=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (value, course_id))
            conn.commit()

    def get_featured_courses(self, limit: int = 20) -> list[dict[str, Any]]:
        with closing(self.get_conn()) as conn:
            rows = conn.execute("""
                SELECT * FROM courses
                WHERE is_featured=1
                ORDER BY updated_at DESC, created_at DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    def get_categories(self) -> list[str]:
        with closing(self.get_conn()) as conn:
            rows = conn.execute("""
                SELECT DISTINCT category
                FROM courses
                WHERE category IS NOT NULL AND TRIM(category) != ''
                ORDER BY category ASC
            """).fetchall()
            return [r[0] for r in rows]

    def get_all_keywords(self) -> list[str]:
        with closing(self.get_conn()) as conn:
            rows = conn.execute("SELECT keyword FROM course_keywords").fetchall()
            return [r["keyword"] for r in rows]

    def log_search(self, user_id: int | None, username: str, query: str, matched_count: int):
        with closing(self.get_conn()) as conn:
            conn.execute("""
                INSERT INTO search_logs (user_id, username, query, matched_count)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, query, matched_count))
            conn.commit()

    def log_click(self, user_id: int | None, username: str, course_id: int, action_type: str):
        with closing(self.get_conn()) as conn:
            conn.execute("""
                INSERT INTO course_clicks (user_id, username, course_id, action_type)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, course_id, action_type))
            conn.commit()

    def add_purchase(self, user_id: int, username: str, course_id: int, payment_note: str = ""):
        with closing(self.get_conn()) as conn:
            conn.execute("""
                INSERT INTO purchases (user_id, username, course_id, payment_note)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, course_id, payment_note))
            conn.commit()

    def approve_purchase(self, user_id: int, course_id: int, approved_by: int):
        with closing(self.get_conn()) as conn:
            conn.execute("""
                UPDATE purchases
                SET status='approved', approved_by=?
                WHERE user_id=? AND course_id=?
            """, (approved_by, user_id, course_id))
            conn.commit()

    def get_stats(self) -> dict[str, Any]:
        with closing(self.get_conn()) as conn:
            total_courses = conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
            total_searches = conn.execute("SELECT COUNT(*) FROM search_logs").fetchone()[0]
            total_paid = conn.execute("SELECT COUNT(*) FROM courses WHERE is_paid=1").fetchone()[0]
            total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            active_24h = conn.execute("""
                SELECT COUNT(*) FROM users
                WHERE datetime(last_seen_at) >= datetime('now', '-1 day')
            """).fetchone()[0]
            active_7d = conn.execute("""
                SELECT COUNT(*) FROM users
                WHERE datetime(last_seen_at) >= datetime('now', '-7 day')
            """).fetchone()[0]

            popular_queries = conn.execute("""
                SELECT query, COUNT(*) as c
                FROM search_logs
                GROUP BY query
                ORDER BY c DESC
                LIMIT 10
            """).fetchall()

            zero_results = conn.execute("""
                SELECT query, COUNT(*) as c
                FROM search_logs
                WHERE matched_count=0
                GROUP BY query
                ORDER BY c DESC
                LIMIT 10
            """).fetchall()

            top_clicked = conn.execute("""
                SELECT c.title, COUNT(*) as ccount
                FROM course_clicks cc
                JOIN courses c ON c.id = cc.course_id
                GROUP BY cc.course_id
                ORDER BY ccount DESC
                LIMIT 10
            """).fetchall()

            return {
                "total_courses": total_courses,
                "total_searches": total_searches,
                "total_paid_courses": total_paid,
                "total_users": total_users,
                "active_24h": active_24h,
                "active_7d": active_7d,
                "popular_queries": [dict(r) for r in popular_queries],
                "zero_results": [dict(r) for r in zero_results],
                "top_clicked": [dict(r) for r in top_clicked],
            }

    def search_courses(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        q = query.strip().lower()
        if not q:
            return []

        with closing(self.get_conn()) as conn:
            course_rows = conn.execute("SELECT * FROM courses").fetchall()
            keyword_rows = conn.execute("SELECT course_id, keyword FROM course_keywords").fetchall()

        keyword_map: dict[int, list[str]] = {}
        for row in keyword_rows:
            keyword_map.setdefault(row["course_id"], []).append(row["keyword"])

        scored: list[tuple[float, dict[str, Any]]] = []

        for row in course_rows:
            course = dict(row)
            searchable_parts = [
                course.get("title", "") or "",
                course.get("instructor", "") or "",
                course.get("category", "") or "",
                course.get("description", "") or "",
            ] + keyword_map.get(course["id"], [])

            haystack = " | ".join(searchable_parts).lower()
            score = 0.0

            if q in haystack:
                score += 120

            for part in searchable_parts:
                p = part.lower()
                if q == p:
                    score += 150
                elif q in p:
                    score += 60
                else:
                    score += SequenceMatcher(None, q, p).ratio() * 25

            if score > 20:
                scored.append((score, course))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [course for _, course in scored[:limit]]