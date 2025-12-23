# Comprehension Agent with optional embedding support
import re
from typing import List, Optional
from langdetect import detect, detect_langs, LangDetectException

from app.agents.base_agent import BaseAgent
from app.models.schemas import (
    CrawlResult,
    ComprehensionResult,
    LanguageInfo,
    Entity,
    PostData,
)
from app.services.nlp_service import NLPService


class ComprehensionAgent(BaseAgent):
    """
    Agent for understanding post content through NLP analysis.
    Extracts language, entities, keywords, sentiment, and topics.
    """
    
    def __init__(self):
        super().__init__("ComprehensionAgent")
        self.nlp_service = NLPService()
        self.arabic_dialect_patterns = {
            "egyptian": [
                r"\bده\b",
                r"\bدي\b",
                r"\bايه\b",
                r"\bكده\b",
                r"\bبتاع\b",
                r"\bعشان\b",
                r"\bازاي\b",
                r"\bليه\b",
                r"\bفين\b",
            ],
            "gulf": [
                r"\bشلون\b",
                r"\bوايد\b",
                r"\bزين\b",
                r"\bحيل\b",
                r"\bجذي\b",
                r"\bاشوف\b",
                r"\bخوش\b",
            ],
            "levantine": [
                r"\bشو\b",
                r"\bهيك\b",
                r"\bكتير\b",
                r"\bمنيح\b",
                r"\bليش\b",
                r"\bهلق\b",
            ],
            "maghrebi": [
                r"\bواش\b",
                r"\bكيفاش\b",
                r"\bبزاف\b",
                r"\bراه\b",
                r"\bديال\b",
            ],
        }

    async def execute(self, crawl_result: CrawlResult) -> List[ComprehensionResult]:
        """
        Process all posts for comprehension analysis.
        
        Args:
            crawl_result: Crawl result containing posts
            
        Returns:
            List of comprehension results, one per post
        """
        self.log_info(f"Processing {len(crawl_result.posts)} posts for comprehension")

        results = []
        for post in crawl_result.posts:
            result = await self._process_post(post)
            results.append(result)

        self.log_info(f"Comprehension complete for {len(results)} posts")
        return results

    async def _process_post(self, post: PostData) -> ComprehensionResult:
        """Process a single post for comprehension."""
        language_info = self._detect_language(post.content)

        entities = self.nlp_service.extract_entities(post.content, language_info.language)

        keywords = self.nlp_service.extract_keywords(post.content, language_info.language)

        sentiment = self.nlp_service.analyze_sentiment(post.content)

        topics = self._extract_topics(post.content, entities, keywords)

        return ComprehensionResult(
            post_id=post.post_id,
            language_info=language_info,
            entities=entities,
            keywords=keywords,
            sentiment=sentiment,
            topics=topics,
        )

    def _detect_language(self, text: str) -> LanguageInfo:
        """Detect language and dialect of text."""
        clean_text = re.sub(r"http\S+|www\.\S+", "", text)
        clean_text = re.sub(r"[^\w\s]", " ", clean_text)
        clean_text = " ".join(clean_text.split())

        if not clean_text or len(clean_text) < 10:
            return LanguageInfo(language="en", dialect=None, confidence=0.5)

        try:
            detected_langs = detect_langs(clean_text)
            primary_lang = detected_langs[0]
            language = primary_lang.lang
            confidence = primary_lang.prob

            dialect = None
            if language == "ar":
                dialect = self._detect_arabic_dialect(clean_text)

            return LanguageInfo(
                language=language,
                dialect=dialect,
                confidence=confidence,
            )

        except LangDetectException:
            if self._contains_arabic(clean_text):
                dialect = self._detect_arabic_dialect(clean_text)
                return LanguageInfo(language="ar", dialect=dialect, confidence=0.7)

            return LanguageInfo(language="en", dialect=None, confidence=0.5)

    def _contains_arabic(self, text: str) -> bool:
        """Check if text contains Arabic characters."""
        arabic_pattern = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+")
        return bool(arabic_pattern.search(text))

    def _detect_arabic_dialect(self, text: str) -> Optional[str]:
        """Detect Arabic dialect from text patterns."""
        dialect_scores = {}

        for dialect, patterns in self.arabic_dialect_patterns.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                score += len(matches)
            dialect_scores[dialect] = score

        if not any(dialect_scores.values()):
            return "modern_standard_arabic"

        detected_dialect = max(dialect_scores, key=dialect_scores.get)
        if dialect_scores[detected_dialect] > 0:
            return detected_dialect

        return "modern_standard_arabic"

    def _extract_topics(
        self, text: str, entities: List[Entity], keywords: List[str]
    ) -> List[str]:
        """Extract topics from text, entities, and keywords."""
        topics = set()

        entity_types_to_topics = {
            "ORG": "organizations",
            "PERSON": "people",
            "GPE": "places",
            "LOC": "locations",
            "EVENT": "events",
            "PRODUCT": "products",
            "WORK_OF_ART": "culture",
            "LAW": "legal",
            "MONEY": "finance",
            "DATE": "timeline",
        }

        for entity in entities:
            if entity.label in entity_types_to_topics:
                topics.add(entity_types_to_topics[entity.label])

        topic_keywords = {
            "politics": ["election", "government", "president", "minister", "parliament"],
            "sports": ["match", "team", "player", "goal", "championship", "league"],
            "technology": ["app", "software", "digital", "internet", "computer", "phone"],
            "economy": ["market", "price", "investment", "stock", "economy", "trade"],
            "health": ["hospital", "doctor", "medicine", "disease", "health", "vaccine"],
            "education": ["school", "university", "student", "education", "teacher"],
            "entertainment": ["movie", "music", "artist", "concert", "show", "celebrity"],
        }

        text_lower = text.lower()
        for topic, kws in topic_keywords.items():
            for kw in kws:
                if kw in text_lower:
                    topics.add(topic)
                    break

        return list(topics)[:10]
