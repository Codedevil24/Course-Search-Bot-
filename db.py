from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row

from config import PAGE_SIZE, SUPABASE_DB_URL
from utils import normalize_text, tokenize_query, unique_keep_order


class Database:
    def __init__(self, db_url: str | None = None):
        self.db_url = db_url or SUPABASE_DB_URL
        if not self.db_url:
            raise ValueError('SUPABASE_DB_URL missing in environment')

    def get_conn(self):
        return psycopg.connect(self.db_url, row_factory=dict_row)

    def init_db(self):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS courses (
                        id BIGSERIAL PRIMARY KEY,
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
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    );
                    '''
                )
                cur.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS keywords (
                        id BIGSERIAL PRIMARY KEY,
                        course_id BIGINT REFERENCES courses(id) ON DELETE CASCADE,
                        keyword TEXT NOT NULL
                    );
                    '''
                )
                cur.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        first_seen TIMESTAMP DEFAULT NOW(),
                        last_seen TIMESTAMP DEFAULT NOW()
                    );
                    '''
                )
                cur.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS searches (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT,
                        username TEXT,
                        query TEXT NOT NULL,
                        matched_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                    '''
                )
                cur.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS course_clicks (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT,
                        username TEXT,
                        course_id BIGINT REFERENCES courses(id) ON DELETE CASCADE,
                        action_type TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                    '''
                )
                cur.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS purchases (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT,
                        username TEXT,
                        course_id BIGINT REFERENCES courses(id) ON DELETE CASCADE,
                        status TEXT DEFAULT 'pending',
                        payment_note TEXT,
                        approved_by BIGINT,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                    '''
                )
                cur.execute('CREATE INDEX IF NOT EXISTS idx_courses_title ON courses USING btree (title);')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_courses_category ON courses USING btree (category);')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON keywords USING btree (keyword);')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_searches_query ON searches USING btree (query);')
            conn.commit()

    def upsert_user(self, user_id: int, username: str = '', first_name: str = '', last_name: str = ''):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    INSERT INTO users (user_id, username, first_name, last_name, first_seen, last_seen)
                    VALUES (%s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (user_id)
                    DO UPDATE SET
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        last_seen = NOW()
                    ''',
                    (user_id, username, first_name, last_name),
                )
            conn.commit()

    def _find_duplicate_course(self, cur, title: str, instructor: str = '') -> dict[str, Any] | None:
        normalized_title = normalize_text(title)
        normalized_instructor = normalize_text(instructor)
        cur.execute(
            '''
            SELECT *
            FROM courses
            WHERE LOWER(TRIM(COALESCE(title, ''))) = LOWER(TRIM(%s))
              AND LOWER(TRIM(COALESCE(instructor, ''))) = LOWER(TRIM(%s))
            ORDER BY id DESC
            LIMIT 1
            ''',
            (normalized_title, normalized_instructor),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def replace_course_keywords(self, course_id: int, keywords: list[str] | None):
        keywords = unique_keep_order([k for k in (keywords or []) if k.strip()])
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM keywords WHERE course_id = %s', (course_id,))
                for kw in keywords:
                    cur.execute('INSERT INTO keywords (course_id, keyword) VALUES (%s, %s)', (course_id, normalize_text(kw)))
            conn.commit()

    def add_course(
        self,
        title: str,
        instructor: str = '',
        category: str = '',
        description: str = '',
        thumbnail: str = '',
        download_url: str = '',
        how_to_download_url: str = '',
        demo_url: str = '',
        contact_url: str = '',
        premium_channel_link: str = '',
        is_featured: bool = False,
        is_paid: bool = False,
        price: str = '',
        keywords: list[str] | None = None,
        allow_reactivate_duplicate: bool = True,
    ) -> tuple[int, bool]:
        keywords = unique_keep_order(keywords or [])
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                existing = self._find_duplicate_course(cur, title, instructor)
                if existing:
                    if allow_reactivate_duplicate and not existing.get('is_active', True):
                        cur.execute(
                            '''
                            UPDATE courses
                            SET category = %s,
                                description = %s,
                                thumbnail = %s,
                                download_url = %s,
                                how_to_download_url = %s,
                                demo_url = %s,
                                contact_url = %s,
                                premium_channel_link = %s,
                                is_featured = %s,
                                is_paid = %s,
                                price = %s,
                                is_active = TRUE,
                                updated_at = NOW()
                            WHERE id = %s
                            ''',
                            (
                                category,
                                description,
                                thumbnail,
                                download_url,
                                how_to_download_url,
                                demo_url,
                                contact_url,
                                premium_channel_link,
                                is_featured,
                                is_paid,
                                price,
                                existing['id'],
                            ),
                        )
                        cur.execute('DELETE FROM keywords WHERE course_id = %s', (existing['id'],))
                        for kw in keywords:
                            cur.execute('INSERT INTO keywords (course_id, keyword) VALUES (%s, %s)', (existing['id'], normalize_text(kw)))
                        conn.commit()
                    return existing['id'], False

                cur.execute(
                    '''
                    INSERT INTO courses (
                        title, instructor, category, description, thumbnail,
                        download_url, how_to_download_url, demo_url, contact_url,
                        premium_channel_link, is_featured, is_paid, price, is_active, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, NOW())
                    RETURNING id
                    ''',
                    (
                        title,
                        instructor,
                        category,
                        description,
                        thumbnail,
                        download_url,
                        how_to_download_url,
                        demo_url,
                        contact_url,
                        premium_channel_link,
                        is_featured,
                        is_paid,
                        price,
                    ),
                )
                course_id = cur.fetchone()['id']
                for kw in keywords:
                    cur.execute('INSERT INTO keywords (course_id, keyword) VALUES (%s, %s)', (course_id, normalize_text(kw)))
            conn.commit()
        return course_id, True

    def update_course_thumbnail(self, course_id: int, thumbnail_file_id: str):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute('UPDATE courses SET thumbnail = %s, updated_at = NOW() WHERE id = %s', (thumbnail_file_id, course_id))
            conn.commit()

    def update_course_fields(self, course_id: int, fields: dict[str, Any], keywords: list[str] | None = None) -> bool:
        allowed = {
            'title', 'instructor', 'category', 'description', 'thumbnail', 'download_url',
            'how_to_download_url', 'demo_url', 'contact_url', 'premium_channel_link',
            'is_featured', 'is_paid', 'price', 'is_active'
        }
        update_fields = {k: v for k, v in fields.items() if k in allowed}
        if not update_fields and keywords is None:
            return False

        with self.get_conn() as conn:
            with conn.cursor() as cur:
                if update_fields:
                    set_sql = ', '.join([f'{key} = %s' for key in update_fields]) + ', updated_at = NOW()'
                    values = list(update_fields.values()) + [course_id]
                    cur.execute(f'UPDATE courses SET {set_sql} WHERE id = %s', values)
                if keywords is not None:
                    cur.execute('DELETE FROM keywords WHERE course_id = %s', (course_id,))
                    for kw in unique_keep_order(keywords):
                        cur.execute('INSERT INTO keywords (course_id, keyword) VALUES (%s, %s)', (course_id, normalize_text(kw)))
            conn.commit()
        return True

    def soft_delete_course(self, course_id: int):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute('UPDATE courses SET is_active = FALSE, updated_at = NOW() WHERE id = %s', (course_id,))
            conn.commit()

    def restore_course(self, course_id: int):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute('UPDATE courses SET is_active = TRUE, updated_at = NOW() WHERE id = %s', (course_id,))
            conn.commit()

    def get_course(self, course_id: int) -> dict[str, Any] | None:
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM courses WHERE id = %s LIMIT 1', (course_id,))
                row = cur.fetchone()
                return dict(row) if row else None

    def get_course_keywords(self, course_id: int) -> list[str]:
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT keyword FROM keywords WHERE course_id = %s ORDER BY keyword ASC', (course_id,))
                return [r['keyword'] for r in cur.fetchall()]

    def list_courses(self, limit: int = 100, active_only: bool = True) -> list[dict[str, Any]]:
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                if active_only:
                    cur.execute('SELECT * FROM courses WHERE is_active = TRUE ORDER BY updated_at DESC, created_at DESC LIMIT %s', (limit,))
                else:
                    cur.execute('SELECT * FROM courses ORDER BY updated_at DESC, created_at DESC LIMIT %s', (limit,))
                return [dict(r) for r in cur.fetchall()]

    def set_featured(self, course_id: int, value: bool):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute('UPDATE courses SET is_featured = %s, updated_at = NOW() WHERE id = %s', (value, course_id))
            conn.commit()

    def get_featured_courses(self, limit: int | None = None, offset: int = 0) -> list[dict[str, Any]]:
        limit = limit or PAGE_SIZE
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT * FROM courses
                    WHERE is_featured = TRUE AND is_active = TRUE
                    ORDER BY updated_at DESC, created_at DESC
                    LIMIT %s OFFSET %s
                    ''',
                    (limit, offset),
                )
                return [dict(r) for r in cur.fetchall()]

    def count_featured_courses(self) -> int:
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT COUNT(*) AS c FROM courses WHERE is_featured = TRUE AND is_active = TRUE')
                return cur.fetchone()['c']

    def get_categories(self) -> list[str]:
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT DISTINCT category
                    FROM courses
                    WHERE is_active = TRUE AND category IS NOT NULL AND TRIM(category) <> ''
                    ORDER BY category ASC
                    '''
                )
                return [r['category'] for r in cur.fetchall()]

    def search_courses_by_category(self, category: str, limit: int | None = None, offset: int = 0) -> list[dict[str, Any]]:
        c = (category or '').strip()
        if not c:
            return []
        limit = limit or PAGE_SIZE
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT *
                    FROM courses
                    WHERE is_active = TRUE AND LOWER(COALESCE(category, '')) = LOWER(%s)
                    ORDER BY updated_at DESC, created_at DESC
                    LIMIT %s OFFSET %s
                    ''',
                    (c, limit, offset),
                )
                return [dict(r) for r in cur.fetchall()]

    def count_courses_by_category(self, category: str) -> int:
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT COUNT(*) AS c FROM courses
                    WHERE is_active = TRUE AND LOWER(COALESCE(category, '')) = LOWER(%s)
                    ''',
                    (category,),
                )
                return cur.fetchone()['c']

    def get_all_keywords(self) -> list[str]:
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT keyword FROM keywords ORDER BY keyword ASC')
                keyword_rows = [r['keyword'] for r in cur.fetchall()]
                cur.execute(
                    '''
                    SELECT title FROM courses WHERE is_active = TRUE
                    UNION
                    SELECT COALESCE(instructor, '') FROM courses WHERE is_active = TRUE
                    UNION
                    SELECT COALESCE(category, '') FROM courses WHERE is_active = TRUE
                    ORDER BY 1 ASC
                    '''
                )
                extras = [r['title'] for r in cur.fetchall() if r['title'].strip()]
                return unique_keep_order(keyword_rows + extras)

    def log_search(self, user_id: int | None, username: str, query: str, matched_count: int):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute('INSERT INTO searches (user_id, username, query, matched_count) VALUES (%s, %s, %s, %s)', (user_id, username, query, matched_count))
            conn.commit()

    def log_click(self, user_id: int | None, username: str, course_id: int, action_type: str):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO course_clicks (user_id, username, course_id, action_type) VALUES (%s, %s, %s, %s)',
                    (user_id, username, course_id, action_type),
                )
            conn.commit()

    def add_purchase(self, user_id: int, username: str, course_id: int, payment_note: str = '') -> tuple[int, str]:
        existing = self.get_purchase(user_id, course_id)
        if existing and existing.get('status') == 'approved':
            return existing['id'], 'approved'
        if existing and existing.get('status') == 'pending':
            return existing['id'], 'pending'

        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO purchases (user_id, username, course_id, payment_note) VALUES (%s, %s, %s, %s) RETURNING id',
                    (user_id, username, course_id, payment_note),
                )
                purchase_id = cur.fetchone()['id']
            conn.commit()
        return purchase_id, 'created'

    def get_purchase(self, user_id: int, course_id: int) -> dict[str, Any] | None:
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT * FROM purchases
                    WHERE user_id = %s AND course_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                    ''',
                    (user_id, course_id),
                )
                row = cur.fetchone()
                return dict(row) if row else None

    def get_pending_purchases(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT p.*, c.title AS course_title
                    FROM purchases p
                    JOIN courses c ON c.id = p.course_id
                    WHERE p.status = 'pending'
                    ORDER BY p.created_at DESC
                    LIMIT %s
                    ''',
                    (limit,),
                )
                return [dict(r) for r in cur.fetchall()]

    def approve_purchase(self, user_id: int, course_id: int, approved_by: int):
        existing = self.get_purchase(user_id, course_id)
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                if existing:
                    cur.execute(
                        '''
                        UPDATE purchases
                        SET status = 'approved', approved_by = %s
                        WHERE id = %s
                        ''',
                        (approved_by, existing['id']),
                    )
                else:
                    cur.execute(
                        '''
                        INSERT INTO purchases (user_id, username, course_id, status, approved_by)
                        VALUES (%s, %s, %s, 'approved', %s)
                        ''',
                        (user_id, '', course_id, approved_by),
                    )
            conn.commit()

    def get_stats(self) -> dict[str, Any]:
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT COUNT(*) AS c FROM courses WHERE is_active = TRUE')
                total_courses = cur.fetchone()['c']
                cur.execute('SELECT COUNT(*) AS c FROM searches')
                total_searches = cur.fetchone()['c']
                cur.execute('SELECT COUNT(*) AS c FROM courses WHERE is_paid = TRUE AND is_active = TRUE')
                total_paid_courses = cur.fetchone()['c']
                cur.execute('SELECT COUNT(*) AS c FROM users')
                total_users = cur.fetchone()['c']
                cur.execute("SELECT COUNT(*) AS c FROM users WHERE last_seen >= NOW() - INTERVAL '1 day'")
                active_24h = cur.fetchone()['c']
                cur.execute("SELECT COUNT(*) AS c FROM users WHERE last_seen >= NOW() - INTERVAL '7 day'")
                active_7d = cur.fetchone()['c']

                cur.execute('SELECT query, COUNT(*) AS c FROM searches GROUP BY query ORDER BY c DESC LIMIT 10')
                popular_queries = [dict(r) for r in cur.fetchall()]

                cur.execute(
                    '''
                    SELECT query, COUNT(*) AS c
                    FROM searches
                    WHERE matched_count = 0
                    GROUP BY query
                    ORDER BY c DESC
                    LIMIT 10
                    '''
                )
                zero_results = [dict(r) for r in cur.fetchall()]

                cur.execute(
                    '''
                    SELECT c.title, COUNT(*) AS ccount
                    FROM course_clicks cc
                    JOIN courses c ON c.id = cc.course_id
                    GROUP BY c.title
                    ORDER BY ccount DESC
                    LIMIT 10
                    '''
                )
                top_clicked = [dict(r) for r in cur.fetchall()]

                cur.execute(
                    '''
                    SELECT COALESCE(category, 'General') AS category, COUNT(*) AS c
                    FROM courses
                    WHERE is_active = TRUE
                    GROUP BY category
                    ORDER BY c DESC
                    LIMIT 10
                    '''
                )
                top_categories = [dict(r) for r in cur.fetchall()]

                cur.execute(
                    '''
                    SELECT COUNT(*) AS pending_count
                    FROM purchases
                    WHERE status = 'pending'
                    '''
                )
                pending_purchases = cur.fetchone()['pending_count']

                return {
                    'total_courses': total_courses,
                    'total_searches': total_searches,
                    'total_paid_courses': total_paid_courses,
                    'total_users': total_users,
                    'active_24h': active_24h,
                    'active_7d': active_7d,
                    'popular_queries': popular_queries,
                    'zero_results': zero_results,
                    'top_clicked': top_clicked,
                    'top_categories': top_categories,
                    'pending_purchases': pending_purchases,
                }



    def get_admin_ids_fallback(self) -> list[int]:
        from config import ADMIN_IDS
        return sorted(ADMIN_IDS)

    def _build_search_sql(self, query: str) -> tuple[str, list[Any], str, list[Any]]:
        q = normalize_text(query)
        tokens = tokenize_query(q)
        exact_q = q
        prefix_q = f'{q}%'
        like_q = f'%{q}%'

        where_parts = [
            "LOWER(COALESCE(c.title, '')) LIKE %s",
            "LOWER(COALESCE(c.instructor, '')) LIKE %s",
            "LOWER(COALESCE(c.category, '')) LIKE %s",
            "LOWER(COALESCE(c.description, '')) LIKE %s",
            "LOWER(COALESCE(k.keyword, '')) LIKE %s",
        ]
        where_params: list[Any] = [like_q, like_q, like_q, like_q, like_q]

        token_score_parts: list[str] = []
        token_score_params: list[Any] = []
        for token in tokens:
            token_like = f'%{token}%'
            where_parts.extend([
                "LOWER(COALESCE(c.title, '')) LIKE %s",
                "LOWER(COALESCE(c.instructor, '')) LIKE %s",
                "LOWER(COALESCE(c.category, '')) LIKE %s",
                "LOWER(COALESCE(c.description, '')) LIKE %s",
                "LOWER(COALESCE(k.keyword, '')) LIKE %s",
            ])
            where_params.extend([token_like, token_like, token_like, token_like, token_like])
            token_score_parts.append(
                "CASE WHEN LOWER(COALESCE(c.title, '')) LIKE %s THEN 8 ELSE 0 END + "
                "CASE WHEN LOWER(COALESCE(k.keyword, '')) LIKE %s THEN 6 ELSE 0 END + "
                "CASE WHEN LOWER(COALESCE(c.instructor, '')) LIKE %s THEN 4 ELSE 0 END + "
                "CASE WHEN LOWER(COALESCE(c.category, '')) LIKE %s THEN 3 ELSE 0 END + "
                "CASE WHEN LOWER(COALESCE(c.description, '')) LIKE %s THEN 1 ELSE 0 END"
            )
            token_score_params.extend([token_like, token_like, token_like, token_like, token_like])

        score_sql = (
            "CASE WHEN LOWER(COALESCE(c.title, '')) = %s THEN 100 ELSE 0 END + "
            "CASE WHEN LOWER(COALESCE(k.keyword, '')) = %s THEN 90 ELSE 0 END + "
            "CASE WHEN LOWER(COALESCE(c.instructor, '')) = %s THEN 70 ELSE 0 END + "
            "CASE WHEN LOWER(COALESCE(c.category, '')) = %s THEN 60 ELSE 0 END + "
            "CASE WHEN LOWER(COALESCE(c.title, '')) LIKE %s THEN 50 ELSE 0 END + "
            "CASE WHEN LOWER(COALESCE(k.keyword, '')) LIKE %s THEN 40 ELSE 0 END + "
            "CASE WHEN LOWER(COALESCE(c.instructor, '')) LIKE %s THEN 25 ELSE 0 END + "
            "CASE WHEN LOWER(COALESCE(c.category, '')) LIKE %s THEN 15 ELSE 0 END + "
            "CASE WHEN LOWER(COALESCE(c.description, '')) LIKE %s THEN 8 ELSE 0 END"
        )
        score_params: list[Any] = [exact_q, exact_q, exact_q, exact_q, prefix_q, prefix_q, like_q, like_q, like_q]
        if token_score_parts:
            score_sql += ' + ' + ' + '.join(f'({part})' for part in token_score_parts)
            score_params.extend(token_score_params)

        where_sql = ' OR '.join(f'({part})' for part in where_parts)
        return score_sql, score_params, where_sql, where_params

    def search_courses(self, query: str, limit: int | None = None, offset: int = 0) -> list[dict[str, Any]]:
        q = normalize_text(query)
        if not q:
            return []
        limit = limit or PAGE_SIZE
        score_sql, score_params, where_sql, where_params = self._build_search_sql(q)
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f'''
                    SELECT ranked.*
                    FROM (
                        SELECT
                            c.*,
                            MAX({score_sql}) AS search_rank
                        FROM courses c
                        LEFT JOIN keywords k ON k.course_id = c.id
                        WHERE c.is_active = TRUE
                          AND ({where_sql})
                        GROUP BY c.id
                    ) AS ranked
                    ORDER BY ranked.search_rank DESC, ranked.updated_at DESC, ranked.created_at DESC
                    LIMIT %s OFFSET %s
                    ''',
                    score_params + where_params + [limit, offset],
                )
                return [dict(r) for r in cur.fetchall()]

    def count_search_courses(self, query: str) -> int:
        q = normalize_text(query)
        if not q:
            return 0
        _, _, where_sql, where_params = self._build_search_sql(q)
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f'''
                    SELECT COUNT(DISTINCT c.id) AS c
                    FROM courses c
                    LEFT JOIN keywords k ON k.course_id = c.id
                    WHERE c.is_active = TRUE
                      AND ({where_sql})
                    ''',
                    where_params,
                )
                return cur.fetchone()['c']

    def search_courses_fallback(self, query: str, limit: int | None = None, offset: int = 0) -> list[dict[str, Any]]:
        q = normalize_text(query)
        if not q:
            return []
        limit = limit or PAGE_SIZE
        tokens = tokenize_query(q)
        like_clauses = [f'%{q}%']
        like_clauses.extend(f'%{token}%' for token in tokens if token != q)

        where_parts: list[str] = []
        params: list[Any] = []
        for like_q in like_clauses:
            where_parts.extend([
                "LOWER(COALESCE(c.title, '')) LIKE %s",
                "LOWER(COALESCE(c.instructor, '')) LIKE %s",
                "LOWER(COALESCE(c.category, '')) LIKE %s",
                "LOWER(COALESCE(c.description, '')) LIKE %s",
                "LOWER(COALESCE(k.keyword, '')) LIKE %s",
            ])
            params.extend([like_q, like_q, like_q, like_q, like_q])

        where_sql = ' OR '.join(f'({part})' for part in where_parts)
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f'''
                    SELECT c.*
                    FROM courses c
                    LEFT JOIN keywords k ON k.course_id = c.id
                    WHERE c.is_active = TRUE
                      AND ({where_sql})
                    GROUP BY c.id
                    ORDER BY c.updated_at DESC, c.created_at DESC
                    LIMIT %s OFFSET %s
                    ''',
                    params + [limit, offset],
                )
                return [dict(r) for r in cur.fetchall()]


db = Database()
