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
                download_url TEXT NOT NULL,
                how_to_download_url TEXT,
                is_featured INTEGER DEFAULT 0,
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

            conn.commit()

    def add_course(
        self,
        title: str,
        instructor: str,
        category: str,
        description: str,
        download_url: str,
        how_to_download_url: str,
        keywords: list[str],
    ) -> int:
        with closing(self.get_conn()) as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO courses (title, instructor, category, description, download_url, how_to_download_url)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (title, instructor, category, description, download_url, how_to_download_url))
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

    def update_course(
        self,
        course_id: int,
        title: str,
        instructor: str,
        category: str,
        description: str,
        download_url: str,
        how_to_download_url: str,
    ):
        with closing(self.get_conn()) as conn:
            conn.execute("""
                UPDATE courses
                SET title=?, instructor=?, category=?, description=?, download_url=?, how_to_download_url=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (title, instructor, category, description, download_url, how_to_download_url, course_id))
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

    def log_search(self, user_id: int | None, username: str, query: str, matched_count: int):
        with closing(self.get_conn()) as conn:
            conn.execute("""
                INSERT INTO search_logs (user_id, username, query, matched_count)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, query, matched_count))
            conn.commit()

    def get_stats(self) -> dict[str, Any]:
        with closing(self.get_conn()) as conn:
            total_courses = conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
            total_searches = conn.execute("SELECT COUNT(*) FROM search_logs").fetchone()[0]
            popular = conn.execute("""
                SELECT query, COUNT(*) as c
                FROM search_logs
                GROUP BY query
                ORDER BY c DESC
                LIMIT 10
            """).fetchall()

            return {
                "total_courses": total_courses,
                "total_searches": total_searches,
                "popular_queries": [dict(r) for r in popular],
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
                score += 100

            for part in searchable_parts:
                p = part.lower()
                if q == p:
                    score += 120
                elif q in p:
                    score += 50
                else:
                    ratio = SequenceMatcher(None, q, p).ratio()
                    score += ratio * 20

            if score > 20:
                scored.append((score, course))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [course for _, course in scored[:limit]]

    def seed_demo_data(self):
        existing = self.list_courses(limit=1)
        if existing:
            return

        self.add_course(
            title="Complete 2025 Python Bootcamp – Learn Python from Scratch",
            instructor="CodeWithHarry",
            category="Python",
            description="Python basics se advanced tak complete bootcamp.",
            download_url="https://gplinks.co/Udemy_python_codewithharry",
            how_to_download_url="https://youtu.be/_p_SeBnl-xE?si=cgjhCJVNP6O-luir",
            keywords=["python", "python bootcamp", "learn python", "codewithharry python"],
        )

        self.add_course(
            title="CampusX – Data Analysis Using Power BI",
            instructor="CampusX",
            category="Data Analysis",
            description="Power BI ke through data analysis course.",
            download_url="https://gplinks.co/CampusX_powerbi",
            how_to_download_url="https://youtu.be/_p_SeBnl-xE?si=cgjhCJVNP6O-luir",
            keywords=["campusx powerbi", "power bi", "data analysis", "powerbi course"],
        )

        self.add_course(
            title="Bitten Tech – Complete Offensive Pentesting Course",
            instructor="Bitten Tech",
            category="Cyber Security",
            description="Offensive pentesting and cyber security focused course.",
            download_url="https://gplinks.co/Bitten_tech_OSCP",
            how_to_download_url="https://youtu.be/_p_SeBnl-xE?si=cgjhCJVNP6O-luir",
            keywords=["pentesting", "oscp", "cyber security", "bitten tech"],
        )

        self.set_featured(1, 1)
        self.set_featured(2, 1)