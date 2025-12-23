from typing import List

from app.agents.base_agent import BaseAgent
from app.models.schemas import ArticleContent, QAScores
from app.services.quality_service import QualityService
from app.config import settings


class QAEngineerAgent(BaseAgent):
    def __init__(self):
        super().__init__("QAEngineerAgent")
        self.quality_service = QualityService()
        self.thresholds = {
            "readability": settings.qa_readability_threshold,
            "coherence": settings.qa_coherence_threshold,
            "redundancy": settings.qa_redundancy_threshold,
            "neutrality": settings.qa_neutrality_threshold,
            "human_likeness": settings.qa_human_likeness_threshold,
        }

    async def execute(self, article_content: ArticleContent) -> QAScores:
        self.log_info(f"Evaluating article quality: {article_content.title}")

        text = article_content.body
        language = article_content.language

        readability = self.quality_service.score_readability(text, language)
        coherence = self.quality_service.score_coherence(text, language)
        redundancy = self.quality_service.score_redundancy(text, language)
        neutrality = self.quality_service.score_neutrality(text, language)
        human_likeness = self.quality_service.score_human_likeness(text, language)

        failed_metrics = []

        if readability < self.thresholds["readability"]:
            failed_metrics.append(f"readability ({readability:.1f} < {self.thresholds['readability']})")

        if coherence < self.thresholds["coherence"]:
            failed_metrics.append(f"coherence ({coherence:.1f} < {self.thresholds['coherence']})")

        if redundancy > self.thresholds["redundancy"]:
            failed_metrics.append(f"redundancy ({redundancy:.1f} > {self.thresholds['redundancy']})")

        if neutrality < self.thresholds["neutrality"]:
            failed_metrics.append(f"neutrality ({neutrality:.1f} < {self.thresholds['neutrality']})")

        if human_likeness < self.thresholds["human_likeness"]:
            failed_metrics.append(f"human_likeness ({human_likeness:.1f} < {self.thresholds['human_likeness']})")

        passed = len(failed_metrics) == 0

        scores = QAScores(
            readability=readability,
            coherence=coherence,
            redundancy=redundancy,
            neutrality=neutrality,
            human_likeness=human_likeness,
            passed=passed,
            failed_metrics=failed_metrics,
        )

        if passed:
            self.log_info("Article passed all quality checks")
        else:
            self.log_warning(f"Article failed quality checks: {', '.join(failed_metrics)}")

        return scores

    def generate_feedback(self, qa_scores: QAScores) -> str:
        feedback_parts = []

        if qa_scores.readability < self.thresholds["readability"]:
            feedback_parts.append(
                "READABILITY: The text is difficult to read. Use shorter sentences, "
                "simpler vocabulary, and clearer paragraph structure."
            )

        if qa_scores.coherence < self.thresholds["coherence"]:
            feedback_parts.append(
                "COHERENCE: The text lacks logical flow. Improve transitions between "
                "paragraphs and ensure ideas are connected smoothly."
            )

        if qa_scores.redundancy > self.thresholds["redundancy"]:
            feedback_parts.append(
                "REDUNDANCY: There is too much repetition. Remove duplicate ideas "
                "and phrases. Consolidate similar information."
            )

        if qa_scores.neutrality < self.thresholds["neutrality"]:
            feedback_parts.append(
                "NEUTRALITY: The tone is too subjective. Remove opinions, promotional "
                "language, and emotional expressions. Use factual, objective language."
            )

        if qa_scores.human_likeness < self.thresholds["human_likeness"]:
            feedback_parts.append(
                "HUMAN-LIKENESS: The text sounds artificial. Add varied sentence lengths, "
                "natural transitions, and avoid repetitive patterns."
            )

        return "\n\n".join(feedback_parts)
