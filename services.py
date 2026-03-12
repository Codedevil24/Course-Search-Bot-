import difflib
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


    def search_by_instructor(self, instructor: str, limit: int, offset: int = 0) -> dict:
        instructor = (instructor or '').strip()
        if not instructor:
            return {'results': [], 'total': 0}
        total = self.db.count_courses_by_instructor(instructor)
        results = self.db.search_courses_by_instructor(instructor, limit=limit, offset=offset)
        return {'results': results, 'total': total}

    def filter_results(self, keyword: str, limit: int, offset: int = 0) -> dict:
        keyword = (keyword or '').strip()
        if not keyword:
            return {'results': [], 'total': 0}
        total = self.db.count_filtered_courses(keyword)
        results = self.db.search_filtered_courses(keyword, limit=limit, offset=offset)
        return {'results': results, 'total': total}


# --- v4.5 typo suggestion ---
def suggest_query(query, options):
    try:
        matches = difflib.get_close_matches(query, options, n=3, cutoff=0.6)
        return matches
    except Exception:
        return []
