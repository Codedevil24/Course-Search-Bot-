from db import Database
from utils import suggest_keyword


class SearchService:
    def __init__(self, db: Database):
        self.db = db

    def search_with_suggestions(self, query: str) -> dict:
        query = (query or "").strip()
        if not query:
            return {"results": [], "suggestions": []}

        results = self.db.search_courses(query, limit=10)
        if results:
            return {"results": results, "suggestions": []}

        all_keywords = self.db.get_all_keywords()
        suggestions = suggest_keyword(query, all_keywords)

        # remove duplicates while keeping order
        seen = set()
        unique_suggestions = []
        for item in suggestions:
            key = item.strip().lower()
            if key and key not in seen:
                seen.add(key)
                unique_suggestions.append(item)

        return {"results": [], "suggestions": unique_suggestions}