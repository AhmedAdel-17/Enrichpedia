import re
import math
from typing import List, Dict
from collections import Counter


class QualityService:
    def __init__(self):
        self.promotional_words_en = [
            "buy", "sale", "discount", "offer", "limited", "exclusive",
            "amazing", "incredible", "best ever", "act now", "hurry",
            "free", "bonus", "guarantee", "order now", "click here",
        ]
        self.promotional_words_ar = [
            "اشتري", "خصم", "عرض", "حصري", "لفترة محدودة", "سارع",
            "مجاني", "فرصة", "لا تفوت", "احجز الآن",
        ]
        self.opinion_words_en = [
            "i think", "i believe", "in my opinion", "i feel",
            "personally", "we believe", "our view", "we think",
        ]
        self.opinion_words_ar = [
            "أعتقد", "في رأيي", "أظن", "أشعر", "نعتقد", "من وجهة نظري",
        ]

    def score_readability(self, text: str, language: str) -> float:
        if not text or len(text) < 50:
            return 50.0

        sentences = self._split_sentences(text)
        words = self._split_words(text)

        if not sentences or not words:
            return 50.0

        avg_sentence_length = len(words) / len(sentences)
        avg_word_length = sum(len(w) for w in words) / len(words)

        if language == "ar":
            sentence_score = max(0, 100 - abs(avg_sentence_length - 15) * 3)
            word_score = max(0, 100 - abs(avg_word_length - 5) * 5)
        else:
            sentence_score = max(0, 100 - abs(avg_sentence_length - 17) * 2.5)
            word_score = max(0, 100 - abs(avg_word_length - 5) * 4)

        paragraph_breaks = text.count("\n\n")
        structure_score = min(100, 60 + paragraph_breaks * 5)

        score = (sentence_score * 0.4 + word_score * 0.3 + structure_score * 0.3)
        return round(min(100, max(0, score)), 1)

    def score_coherence(self, text: str, language: str) -> float:
        if not text or len(text) < 100:
            return 50.0

        sentences = self._split_sentences(text)
        if len(sentences) < 2:
            return 60.0

        transition_words_en = [
            "however", "therefore", "furthermore", "moreover", "additionally",
            "consequently", "meanwhile", "nevertheless", "nonetheless",
            "in addition", "as a result", "on the other hand", "in contrast",
            "similarly", "likewise", "for example", "for instance",
        ]
        transition_words_ar = [
            "ومع ذلك", "لذلك", "علاوة على ذلك", "بالإضافة إلى", "وبالتالي",
            "في الوقت نفسه", "من ناحية أخرى", "على سبيل المثال", "بالمثل",
            "أيضا", "كذلك", "إضافة إلى", "فضلا عن",
        ]

        transition_words = transition_words_ar if language == "ar" else transition_words_en
        text_lower = text.lower()

        transition_count = sum(1 for tw in transition_words if tw in text_lower)
        transition_score = min(100, 50 + transition_count * 8)

        word_overlap_scores = []
        for i in range(len(sentences) - 1):
            words1 = set(self._split_words(sentences[i].lower()))
            words2 = set(self._split_words(sentences[i + 1].lower()))
            if words1 and words2:
                overlap = len(words1 & words2) / min(len(words1), len(words2))
                word_overlap_scores.append(overlap)

        overlap_score = 100 if not word_overlap_scores else (
            sum(word_overlap_scores) / len(word_overlap_scores) * 150
        )
        overlap_score = min(100, overlap_score)

        paragraph_count = len([p for p in text.split("\n\n") if p.strip()])
        structure_score = min(100, 50 + paragraph_count * 8)

        score = transition_score * 0.4 + overlap_score * 0.35 + structure_score * 0.25
        return round(min(100, max(0, score)), 1)

    def score_redundancy(self, text: str, language: str) -> float:
        if not text or len(text) < 100:
            return 20.0

        sentences = self._split_sentences(text)
        words = self._split_words(text.lower())

        if len(words) < 10:
            return 20.0

        word_freq = Counter(words)
        total_words = len(words)
        unique_words = len(word_freq)

        lexical_diversity = unique_words / total_words
        diversity_penalty = max(0, (0.5 - lexical_diversity) * 100)

        repeated_phrases = 0
        for i in range(len(sentences)):
            for j in range(i + 1, len(sentences)):
                similarity = self._sentence_similarity(sentences[i], sentences[j])
                if similarity > 0.6:
                    repeated_phrases += 1

        phrase_penalty = min(50, repeated_phrases * 10)

        high_freq_penalty = 0
        for word, count in word_freq.most_common(10):
            if len(word) > 3 and count > 5:
                high_freq_penalty += (count - 5) * 2

        high_freq_penalty = min(30, high_freq_penalty)

        score = diversity_penalty + phrase_penalty + high_freq_penalty
        return round(min(100, max(0, score)), 1)

    def score_neutrality(self, text: str, language: str) -> float:
        if not text:
            return 50.0

        text_lower = text.lower()

        promotional_words = (
            self.promotional_words_ar if language == "ar" else self.promotional_words_en
        )
        opinion_words = (
            self.opinion_words_ar if language == "ar" else self.opinion_words_en
        )

        promotional_count = sum(1 for word in promotional_words if word in text_lower)
        opinion_count = sum(1 for word in opinion_words if word in text_lower)

        exclamation_count = text.count("!")
        all_caps_words = len(re.findall(r"\b[A-Z]{3,}\b", text))

        promotional_penalty = min(30, promotional_count * 8)
        opinion_penalty = min(25, opinion_count * 7)
        exclamation_penalty = min(20, exclamation_count * 5)
        caps_penalty = min(15, all_caps_words * 5)

        score = 100 - promotional_penalty - opinion_penalty - exclamation_penalty - caps_penalty
        return round(max(0, min(100, score)), 1)

    def score_human_likeness(self, text: str, language: str) -> float:
        if not text or len(text) < 100:
            return 60.0

        sentences = self._split_sentences(text)
        if len(sentences) < 3:
            return 60.0

        sentence_lengths = [len(self._split_words(s)) for s in sentences]
        if len(sentence_lengths) >= 2:
            mean_length = sum(sentence_lengths) / len(sentence_lengths)
            variance = sum((l - mean_length) ** 2 for l in sentence_lengths) / len(sentence_lengths)
            std_dev = math.sqrt(variance)
            variation_score = min(100, 50 + std_dev * 5)
        else:
            variation_score = 50

        words = self._split_words(text)
        bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
        bigram_freq = Counter(bigrams)
        repeated_bigrams = sum(1 for count in bigram_freq.values() if count > 2)
        repetition_penalty = min(30, repeated_bigrams * 3)

        contractions = ["n't", "'s", "'re", "'ll", "'ve", "'m", "'d"]
        contraction_count = sum(1 for c in contractions if c in text.lower())
        natural_bonus = min(15, contraction_count * 3)

        paragraph_count = len([p for p in text.split("\n\n") if p.strip()])
        structure_bonus = min(15, paragraph_count * 3)

        score = variation_score - repetition_penalty + natural_bonus + structure_bonus
        return round(max(0, min(100, score)), 1)

    def _split_sentences(self, text: str) -> List[str]:
        sentence_endings = re.compile(r'[.!?؟。]+')
        sentences = sentence_endings.split(text)
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]

    def _split_words(self, text: str) -> List[str]:
        words = re.findall(r'\b[\w\u0600-\u06FF]+\b', text)
        return [w for w in words if len(w) > 1]

    def _sentence_similarity(self, s1: str, s2: str) -> float:
        words1 = set(self._split_words(s1.lower()))
        words2 = set(self._split_words(s2.lower()))
        if not words1 or not words2:
            return 0.0
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0
