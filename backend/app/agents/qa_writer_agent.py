from typing import List, Tuple

from app.agents.base_agent import BaseAgent
from app.agents.generation_agent import GenerationAgent
from app.agents.qa_engineer_agent import QAEngineerAgent
from app.models.schemas import (
    ArticleContent,
    ArticlePlan,
    CrawlResult,
    ComprehensionResult,
    QAScores,
)
from app.config import settings


class QAWriterAgent(BaseAgent):
    def __init__(self):
        super().__init__("QAWriterAgent")
        self.generation_agent = GenerationAgent()
        self.qa_engineer_agent = QAEngineerAgent()
        self.max_retries = settings.max_qa_retries

    async def execute(
        self,
        article_content: ArticleContent,
        qa_scores: QAScores,
        article_plan: ArticlePlan,
        crawl_result: CrawlResult,
        comprehension_results: List[ComprehensionResult],
    ) -> Tuple[ArticleContent, QAScores]:
        """Revise a single article until it passes QA or max retries reached."""
        self.log_info(f"Starting article revision process for: {article_content.title}")

        current_content = article_content
        current_scores = qa_scores
        retry_count = 0

        while not current_scores.passed and retry_count < self.max_retries:
            retry_count += 1
            self.log_info(f"Revision attempt {retry_count}/{self.max_retries}")

            feedback = self.qa_engineer_agent.generate_feedback(current_scores)

            revised_contents = await self.generation_agent.execute(
                article_plans=[article_plan],
                crawl_result=crawl_result,
                comprehension_results=comprehension_results,
                feedback=feedback,
            )
            
            if revised_contents:
                current_content = revised_contents[0]

            current_scores = await self.qa_engineer_agent.execute(current_content)

            if current_scores.passed:
                self.log_info(f"Article passed after {retry_count} revision(s)")
                break

        if not current_scores.passed:
            self.log_warning(
                f"Article did not pass after {self.max_retries} revisions. "
                f"Final scores: R={current_scores.readability:.1f}, "
                f"C={current_scores.coherence:.1f}, "
                f"X={current_scores.redundancy:.1f}, "
                f"N={current_scores.neutrality:.1f}, "
                f"H={current_scores.human_likeness:.1f}"
            )

        return current_content, current_scores
