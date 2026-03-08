from __future__ import annotations

from typing import Any
import psycopg
from psycopg.rows import dict_row

from config import SUPABASE_DB_URL


class Database:
    def __init__(self, db_url: str | None = None):
        self.db_url = db_url or SUPABASE_DB_URL
        if not self.db_url:
            raise ValueError("SUPABASE_DB_URL missing in environment")

    def get_conn(self):
        return psycopg.connect(self.db_url,row_factory=dict_row)

    def init_db(self):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                CREATE TABLE IF NOT EXISTS courses (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    instructor TEXT,
                    category TEXT,
                    description TEXT,
                    thumbnail TEXT,
                    download_url TEXT,
                    how_to_download_url TEXT,
                    demo_url TEXT,
                    contact_url TEXT,
                    premium_channel_link TEXT,
                    is_featured BOOLEAN DEFAULT FALSE,
                    is_paid BOOLEAN DEFAULT FALSE,
                    price TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
                """)

                cur.execute("""
                CREATE TABLE IF NOT EXISTS keywords (
                    id SERIAL PRIMARY KEY,
                    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
                    keyword TEXT NOT NULL
                );
                """)

                cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    first_seen TIMESTAMP DEFAULT NOW(),
                    last_seen TIMESTAMP DEFAULT NOW()
                );
                """)

                cur.execute("""
                CREATE TABLE IF NOT EXISTS searches (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    username TEXT,
                    query TEXT NOT NULL,
                    matched_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                """)

                cur.execute("""
                CREATE TABLE IF NOT EXISTS course_clicks (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    username TEXT,
                    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
                    action_type TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                """)

                cur.execute("""
                CREATE TABLE IF NOT EXISTS purchases (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    username TEXT,
                    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
                    status TEXT DEFAULT 'pending',
                    payment_note TEXT,
                    approved_by BIGINT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                """)

    def upsert_user(self, user_id: int, username: str = "", first_name: str = "", last_name: str = ""):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                INSERT INTO users (user_id, username, first_name, last_name, first_seen, last_seen)
                VALUES (%s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (user_id)
                DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    last_seen = NOW()
                """, (user_id, username, first_name, last_name))

    def add_course(
        self,
        title: str,
        instructor: str,
        category: str,
        description: str,
        thumbnail: str,
        download_url: str,
        how_to_download_url: str,
        demo_url: str,
        contact_url: str,
        premium_channel_link: str,
        is_featured: bool,
        is_paid: bool,
        price: str,
        keywords: list[str],
    ) -> int:
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                INSERT INTO courses (
                    title, instructor, category, description, thumbnail,
                    download_url, how_to_download_url, demo_url, contact_url,
                    premium_channel_link, is_featured, is_paid, price, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
                """, (
                    title, instructor, category, description, thumbnail,
                    download_url, how_to_download_url, demo_url, contact_url,
                    premium_channel_link, is_featured, is_paid, price
                ))
                course_id = cur.fetchone()[0]

                for kw in keywords:
                    kw = kw.strip().lower()
                    if kw:
                        cur.execute(
                            "INSERT INTO keywords (course_id, keyword) VALUES (%s, %s)",
                            (course_id, kw),
                        )

                return course_id

    def update_course_thumbnail(self, course_id: int, thumbnail_file_id: str):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                UPDATE courses
                SET thumbnail=%s, updated_at=NOW()
                WHERE id=%s
                """, (thumbnail_file_id, course_id))

    def delete_course(self, course_id: int):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM courses WHERE id=%s", (course_id,))

    def get_course(self, course_id: int) -> dict[str, Any] | None:
        with self.get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM courses WHERE id=%s", (course_id,))
                row = cur.fetchone()
                return dict(row) if row else None

    def list_courses(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                SELECT * FROM courses
                ORDER BY updated_at DESC, created_at DESC
                LIMIT %s
                """, (limit,))
                return [dict(r) for r in cur.fetchall()]

    def set_featured(self, course_id: int, value: bool):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                UPDATE courses
                SET is_featured=%s, updated_at=NOW()
                WHERE id=%s
                """, (value, course_id))

    def get_featured_courses(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                SELECT * FROM courses
                WHERE is_featured=TRUE
                ORDER BY updated_at DESC, created_at DESC
                LIMIT %s
                """, (limit,))
                return [dict(r) for r in cur.fetchall()]

    def get_categories(self) -> list[str]:
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                SELECT DISTINCT category
                FROM courses
                WHERE category IS NOT NULL AND TRIM(category) <> ''
                ORDER BY category ASC
                """)
                return [r[0] for r in cur.fetchall()]

    def get_all_keywords(self) -> list[str]:
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT keyword FROM keywords")
                return [r[0] for r in cur.fetchall()]

    def log_search(self, user_id: int | None, username: str, query: str, matched_count: int):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                INSERT INTO searches (user_id, username, query, matched_count)
                VALUES (%s, %s, %s, %s)
                """, (user_id, username, query, matched_count))

    def log_click(self, user_id: int | None, username: str, course_id: int, action_type: str):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                INSERT INTO course_clicks (user_id, username, course_id, action_type)
                VALUES (%s, %s, %s, %s)
                """, (user_id, username, course_id, action_type))

    def add_purchase(self, user_id: int, username: str, course_id: int, payment_note: str = ""):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                INSERT INTO purchases (user_id, username, course_id, payment_note)
                VALUES (%s, %s, %s, %s)
                """, (user_id, username, course_id, payment_note))

    def approve_purchase(self, user_id: int, course_id: int, approved_by: int):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                UPDATE purchases
                SET status='approved', approved_by=%s
                WHERE user_id=%s AND course_id=%s
                """, (approved_by, user_id, course_id))

    def get_stats(self) -> dict[str, Any]:
        with self.get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT COUNT(*) AS c FROM courses")
                total_courses = cur.fetchone()["c"]

                cur.execute("SELECT COUNT(*) AS c FROM searches")
                total_searches = cur.fetchone()["c"]

                cur.execute("SELECT COUNT(*) AS c FROM courses WHERE is_paid=TRUE")
                total_paid_courses = cur.fetchone()["c"]

                cur.execute("SELECT COUNT(*) AS c FROM users")
                total_users = cur.fetchone()["c"]

                cur.execute("""
                SELECT COUNT(*) AS c
                FROM users
                WHERE last_seen >= NOW() - INTERVAL '1 day'
                """)
                active_24h = cur.fetchone()["c"]

                cur.execute("""
                SELECT COUNT(*) AS c
                FROM users
                WHERE last_seen >= NOW() - INTERVAL '7 day'
                """)
                active_7d = cur.fetchone()["c"]

                cur.execute("""
                SELECT query, COUNT(*) AS c
                FROM searches
                GROUP BY query
                ORDER BY c DESC
                LIMIT 10
                """)
                popular_queries = [dict(r) for r in cur.fetchall()]

                cur.execute("""
                SELECT query, COUNT(*) AS c
                FROM searches
                WHERE matched_count=0
                GROUP BY query
                ORDER BY c DESC
                LIMIT 10
                """)
                zero_results = [dict(r) for r in cur.fetchall()]

                cur.execute("""
                SELECT c.title, COUNT(*) AS ccount
                FROM course_clicks cc
                JOIN courses c ON c.id = cc.course_id
                GROUP BY c.title
                ORDER BY ccount DESC
                LIMIT 10
                """)
                top_clicked = [dict(r) for r in cur.fetchall()]

                return {
                    "total_courses": total_courses,
                    "total_searches": total_searches,
                    "total_paid_courses": total_paid_courses,
                    "total_users": total_users,
                    "active_24h": active_24h,
                    "active_7d": active_7d,
                    "popular_queries": popular_queries,
                    "zero_results": zero_results,
                    "top_clicked": top_clicked,
                }

    def search_courses(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        q = query.strip().lower()
        if not q:
            return []

        with self.get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                SELECT c.*
                FROM courses c
                LEFT JOIN keywords k ON k.course_id = c.id
                WHERE
                    LOWER(c.title) LIKE %s OR
                    LOWER(COALESCE(c.instructor, '')) LIKE %s OR
                    LOWER(COALESCE(c.category, '')) LIKE %s OR
                    LOWER(COALESCE(c.description, '')) LIKE %s OR
                    LOWER(COALESCE(k.keyword, '')) LIKE %s
                GROUP BY c.id
                ORDER BY c.updated_at DESC
                LIMIT %s
                """, (
                    f"%{q}%",
                    f"%{q}%",
                    f"%{q}%",
                    f"%{q}%",
                    f"%{q}%",
                    limit,
                ))
                return [dict(r) for r in cur.fetchall()]