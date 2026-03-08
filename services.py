from db import Database
from utils import suggest_keyword


class SearchService:
    def __init__(self, db: Database):
        self.db = db

    def search_with_suggestions(self, query: str):
        results = self.db.search_courses(query, limit=10)
        if results:
            return {"results": results, "suggestions": []}

        all_keywords = self.db.get_all_keywords()
        suggestions = suggest_keyword(query, all_keywords)
        return {"results": [], "suggestions": suggestions}