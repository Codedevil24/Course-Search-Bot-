from db import Database
from utils import unique_keep_order, suggest_keyword


class SearchService:
    def __init__(self, db: Database):
        self.db = db

    def search_with_suggestions(self, query: str, limit: int, offset: int = 0) -> dict:
        query = (query or '').strip()
        if not query:
            return {'results': [], 'suggestions': [], 'total': 0}

        total = 0
        results = []
        try:
            total = self.db.count_search_courses(query)
            results = self.db.search_courses(query, limit=limit, offset=offset)
        except Exception:
            total = 0
            results = []

        if results:
            return {'results': results, 'suggestions': [], 'total': total}

        try:
            fallback_results = self.db.search_courses_fallback(query, limit=limit, offset=offset)
        except Exception:
            fallback_results = []

        if fallback_results:
            fallback_total = len(fallback_results) if offset == 0 else max(total, offset + len(fallback_results))
            return {'results': fallback_results, 'suggestions': [], 'total': fallback_total}

        suggestions = unique_keep_order(suggest_keyword(query, self.db.get_all_keywords()))[:10]
        return {'results': [], 'suggestions': suggestions, 'total': 0}
