import re
from typing import List, Dict
from collections import Counter

from app.agents.base_agent import BaseAgent
from app.models.schemas import ComprehensionResult, TagResult


class TaggingAgent(BaseAgent):
    def __init__(self):
        super().__init__("TaggingAgent")
        self.category_keywords = {
            "news": [
                "breaking",
                "report",
                "announced",
                "statement",
                "official",
                "update",
                "today",
                "yesterday",
            ],
            "opinion": [
                "think",
                "believe",
                "opinion",
                "view",
                "perspective",
                "feel",
                "should",
            ],
            "event": [
                "event",
                "happening",
                "celebration",
                "festival",
                "ceremony",
                "conference",
            ],
            "announcement": [
                "announcing",
                "new",
                "launch",
                "introducing",
                "release",
                "available",
            ],
            "educational": [
                "learn",
                "how to",
                "guide",
                "tutorial",
                "tips",
                "explained",
            ],
            "promotional": [
                "sale",
                "discount",
                "offer",
                "buy",
                "price",
                "limited",
                "exclusive",
            ],
            "community": [
                "community",
                "together",
                "support",
                "help",
                "volunteer",
                "donation",
            ],
            "entertainment": [
                "watch",
                "listen",
                "enjoy",
                "fun",
                "amazing",
                "incredible",
            ],
        }
        self.arabic_category_keywords = {
            "news": ["خبر", "عاجل", "تقرير", "رسمي", "اليوم", "أعلن"],
            "opinion": ["رأي", "أعتقد", "أظن", "وجهة نظر", "يجب"],
            "event": ["حدث", "احتفال", "مهرجان", "مؤتمر", "حفل"],
            "announcement": ["إعلان", "جديد", "إطلاق", "متاح"],
            "educational": ["تعلم", "دليل", "نصائح", "شرح"],
            "promotional": ["خصم", "عرض", "سعر", "اشتري"],
            "community": ["مجتمع", "دعم", "مساعدة", "تبرع"],
            "entertainment": ["شاهد", "استمع", "ممتع", "رائع"],
        }

    async def execute(
        self, comprehension_results: List[ComprehensionResult]
    ) -> List[TagResult]:
        self.log_info(f"Tagging {len(comprehension_results)} posts")

        results = []
        for comp_result in comprehension_results:
            tag_result = self._tag_post(comp_result)
            results.append(tag_result)

        self.log_info(f"Tagging complete for {len(results)} posts")
        return results

    def _tag_post(self, comp_result: ComprehensionResult) -> TagResult:
        text = self._get_text_for_tagging(comp_result)
        is_arabic = comp_result.language_info.language == "ar"

        categories = self._determine_categories(text, is_arabic)

        tags = self._generate_tags(comp_result, text, is_arabic)

        importance_score = self._calculate_importance(comp_result, categories)

        return TagResult(
            post_id=comp_result.post_id,
            categories=categories,
            tags=tags,
            importance_score=importance_score,
        )

    def _get_text_for_tagging(self, comp_result: ComprehensionResult) -> str:
        text_parts = [comp_result.post_id]
        text_parts.extend(comp_result.keywords)
        text_parts.extend(comp_result.topics)
        for entity in comp_result.entities:
            text_parts.append(entity.text)
        return " ".join(text_parts).lower()

    def _determine_categories(self, text: str, is_arabic: bool) -> List[str]:
        category_scores: Dict[str, int] = Counter()

        keywords_dict = (
            self.arabic_category_keywords if is_arabic else self.category_keywords
        )

        for category, keywords in keywords_dict.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    category_scores[category] += 1

        if not category_scores:
            return ["general"]

        sorted_categories = sorted(
            category_scores.items(), key=lambda x: x[1], reverse=True
        )
        return [cat for cat, score in sorted_categories[:3] if score > 0]

    def _generate_tags(
        self, comp_result: ComprehensionResult, text: str, is_arabic: bool
    ) -> List[str]:
        tags = set()

        for entity in comp_result.entities[:10]:
            clean_tag = self._clean_tag(entity.text)
            if clean_tag and len(clean_tag) > 2:
                tags.add(clean_tag)

        for keyword in comp_result.keywords[:10]:
            clean_tag = self._clean_tag(keyword)
            if clean_tag and len(clean_tag) > 2:
                tags.add(clean_tag)

        for topic in comp_result.topics:
            tags.add(topic.lower())

        if comp_result.language_info.dialect:
            tags.add(comp_result.language_info.dialect)

        tags.add(comp_result.language_info.language)

        return list(tags)[:20]

    def _clean_tag(self, tag: str) -> str:
        tag = re.sub(r"[^\w\s\u0600-\u06FF]", "", tag)
        tag = " ".join(tag.split())
        return tag.lower().strip()

    def _calculate_importance(
        self, comp_result: ComprehensionResult, categories: List[str]
    ) -> float:
        score = 0.5

        entity_count = len(comp_result.entities)
        score += min(entity_count * 0.05, 0.2)

        keyword_count = len(comp_result.keywords)
        score += min(keyword_count * 0.03, 0.15)

        if "news" in categories or "announcement" in categories:
            score += 0.1

        if comp_result.sentiment in ["positive", "negative"]:
            score += 0.05

        return min(score, 1.0)
