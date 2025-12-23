import re
from typing import List, Optional
import spacy
from spacy.language import Language

from app.models.schemas import Entity


class NLPService:
    def __init__(self):
        self._nlp_en: Optional[Language] = None
        self._nlp_ar: Optional[Language] = None
        self._models_loaded = False

    def _load_models(self) -> None:
        if self._models_loaded:
            return

        try:
            self._nlp_en = spacy.load("en_core_web_sm")
        except OSError:
            self._nlp_en = spacy.blank("en")

        try:
            self._nlp_ar = spacy.blank("ar")
        except Exception:
            self._nlp_ar = spacy.blank("ar")

        self._models_loaded = True

    def _get_nlp(self, language: str) -> Language:
        self._load_models()
        if language == "ar":
            return self._nlp_ar
        return self._nlp_en

    def extract_entities(self, text: str, language: str) -> List[Entity]:
        nlp = self._get_nlp(language)
        doc = nlp(text[:10000])

        entities = []
        for ent in doc.ents:
            entities.append(
                Entity(
                    text=ent.text,
                    label=ent.label_,
                    start=ent.start_char,
                    end=ent.end_char,
                )
            )

        if not entities and language == "ar":
            entities = self._extract_arabic_entities(text)

        return entities[:50]

    def _extract_arabic_entities(self, text: str) -> List[Entity]:
        entities = []

        org_patterns = [
            r"شركة\s+[\u0600-\u06FF\s]+",
            r"مؤسسة\s+[\u0600-\u06FF\s]+",
            r"جمعية\s+[\u0600-\u06FF\s]+",
            r"منظمة\s+[\u0600-\u06FF\s]+",
            r"وزارة\s+[\u0600-\u06FF\s]+",
        ]

        for pattern in org_patterns:
            for match in re.finditer(pattern, text):
                entities.append(
                    Entity(
                        text=match.group().strip(),
                        label="ORG",
                        start=match.start(),
                        end=match.end(),
                    )
                )

        person_patterns = [
            r"الدكتور\s+[\u0600-\u06FF\s]+",
            r"الأستاذ\s+[\u0600-\u06FF\s]+",
            r"السيد\s+[\u0600-\u06FF\s]+",
            r"الشيخ\s+[\u0600-\u06FF\s]+",
        ]

        for pattern in person_patterns:
            for match in re.finditer(pattern, text):
                entities.append(
                    Entity(
                        text=match.group().strip(),
                        label="PERSON",
                        start=match.start(),
                        end=match.end(),
                    )
                )

        return entities

    def extract_keywords(self, text: str, language: str) -> List[str]:
        nlp = self._get_nlp(language)
        doc = nlp(text[:10000])

        keywords = []
        seen = set()

        for token in doc:
            if (
                token.pos_ in ["NOUN", "PROPN", "ADJ"]
                and not token.is_stop
                and len(token.text) > 2
                and token.text.lower() not in seen
            ):
                keywords.append(token.text)
                seen.add(token.text.lower())

        if not keywords:
            keywords = self._extract_keywords_simple(text, language)

        return keywords[:30]

    def _extract_keywords_simple(self, text: str, language: str) -> List[str]:
        words = re.findall(r"\b[\w\u0600-\u06FF]{3,}\b", text)

        stopwords_en = {
            "the", "and", "for", "are", "but", "not", "you", "all", "can",
            "had", "her", "was", "one", "our", "out", "has", "have", "been",
            "this", "that", "with", "they", "from", "which", "will", "would",
        }
        stopwords_ar = {
            "من", "في", "على", "إلى", "عن", "مع", "هذا", "هذه", "التي",
            "الذي", "كان", "كانت", "هو", "هي", "أن", "إن", "لا", "ما",
        }

        stopwords = stopwords_ar if language == "ar" else stopwords_en

        keywords = []
        seen = set()
        for word in words:
            word_lower = word.lower()
            if word_lower not in stopwords and word_lower not in seen:
                keywords.append(word)
                seen.add(word_lower)

        return keywords

    def analyze_sentiment(self, text: str) -> str:
        positive_en = ["good", "great", "excellent", "amazing", "wonderful", "love", "best", "happy", "success"]
        negative_en = ["bad", "terrible", "awful", "hate", "worst", "sad", "fail", "problem", "issue"]

        positive_ar = ["ممتاز", "رائع", "جميل", "أحب", "نجاح", "سعيد", "مبارك", "عظيم"]
        negative_ar = ["سيء", "فشل", "مشكلة", "حزين", "أكره", "سوء"]

        text_lower = text.lower()

        pos_count = sum(1 for word in positive_en + positive_ar if word in text_lower)
        neg_count = sum(1 for word in negative_en + negative_ar if word in text_lower)

        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        return "neutral"
