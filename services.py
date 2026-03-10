from db import Database
from utils import unique_keep_order, suggest_keyword


class SearchService:
    def __init__(self, db: Database):
        self.db = db

    def search_with_suggestions(self, query: str, limit: int, offset: int = 0) -> dict:
        query = (query or '').strip()
        if not query:
            return {'results': [], 'suggestions': [], 'total': 0}

        total = self.db.count_search_courses(query)
        results = self.db.search_courses(query, limit=limit, offset=offset)
        if results:
            return {'results': results, 'suggestions': [], 'total': total}

        suggestions = unique_keep_order(suggest_keyword(query, self.db.get_all_keywords()))
        return {'results': [], 'suggestions': suggestions, 'total': 0}
