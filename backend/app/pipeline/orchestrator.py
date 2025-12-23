from typing import Optional, List
import logging

from app.agents.input_agent import InputAgent
from app.agents.facebook_access_agent import FacebookAccessAgent
from app.agents.crawling_agent import CrawlingAgent
from app.agents.comprehension_agent import ComprehensionAgent
from app.agents.tagging_agent import TaggingAgent
from app.agents.planning_agent import PlanningAgent
from app.agents.generation_agent import GenerationAgent
from app.agents.publishing_agent import PublishingAgent
from app.agents.qa_engineer_agent import QAEngineerAgent
from app.agents.qa_writer_agent import QAWriterAgent
from app.models.schemas import ProcessResponse, Article, ArticlePlan, ArticleContent, QAScores


class PipelineOrchestrator:
    def __init__(self):
        self.logger = logging.getLogger("pipeline.orchestrator")
        logging.basicConfig(level=logging.INFO)

        self.input_agent = InputAgent()
        self.facebook_access_agent = FacebookAccessAgent()
        self.crawling_agent = CrawlingAgent()
        self.comprehension_agent = ComprehensionAgent()
        self.tagging_agent = TaggingAgent()
        self.planning_agent = PlanningAgent()
        self.generation_agent = GenerationAgent()
        self.publishing_agent = PublishingAgent()
        self.qa_engineer_agent = QAEngineerAgent()
        self.qa_writer_agent = QAWriterAgent()

    async def process(self, url: str) -> ProcessResponse:
        self.logger.info(f"Starting pipeline for URL: {url}")

        try:
            input_result = await self.input_agent.execute(url)

            if not input_result.is_valid:
                return ProcessResponse(
                    success=False,
                    article_id=None,
                    article_ids=[],
                    article_count=0,
                    message=f"Invalid URL: {input_result.error}",
                    qa_scores=None,
                )

            self.logger.info(f"Step 1: Input validated - {input_result.url_type.value}")

            scrape_result = await self.facebook_access_agent.execute(input_result)
            self.logger.info("Step 2: Browser scraping completed")

            try:
                crawl_result = await self.crawling_agent.execute(scrape_result, input_result)
                self.logger.info(f"Step 3: Extracted {crawl_result.total_posts} posts")

                if crawl_result.total_posts == 0:
                    return ProcessResponse(
                        success=False,
                        article_id=None,
                        article_ids=[],
                        article_count=0,
                        message="No content found on the page",
                        qa_scores=None,
                    )

                comprehension_results = await self.comprehension_agent.execute(crawl_result)
                self.logger.info(f"Step 4: Comprehension complete for {len(comprehension_results)} posts")

                tag_results = await self.tagging_agent.execute(comprehension_results)
                self.logger.info(f"Step 5: Tagging complete")

                article_plans: List[ArticlePlan] = await self.planning_agent.execute(
                    crawl_result,
                    comprehension_results,
                    tag_results,
                )
                self.logger.info(f"Step 6: Created {len(article_plans)} article plans")

                article_contents: List[ArticleContent] = await self.generation_agent.execute(
                    article_plans,
                    crawl_result,
                    comprehension_results,
                )
                self.logger.info(f"Step 7: Generated {len(article_contents)} articles")

                published_articles: List[Article] = []
                all_qa_scores: List[QAScores] = []

                for idx, (plan, content) in enumerate(zip(article_plans, article_contents)):
                    self.logger.info(f"Step 8.{idx+1}: QA for article '{content.title}'")

                    qa_scores = await self.qa_engineer_agent.execute(content)
                    
                    self.logger.info(
                        f"  QA scores - Passed: {qa_scores.passed}, "
                        f"R={qa_scores.readability:.1f}, C={qa_scores.coherence:.1f}, "
                        f"X={qa_scores.redundancy:.1f}, N={qa_scores.neutrality:.1f}, "
                        f"H={qa_scores.human_likeness:.1f}"
                    )

                    if not qa_scores.passed:
                        content, qa_scores = await self.qa_writer_agent.execute(
                            content,
                            qa_scores,
                            plan,
                            crawl_result,
                            comprehension_results,
                        )
                        self.logger.info(f"  Article revised by QA Writer")

                    article = await self.publishing_agent.execute(
                        content,
                        input_result,
                        tag_results,
                        qa_scores,
                    )
                    
                    published_articles.append(article)
                    all_qa_scores.append(qa_scores)
                    self.logger.info(f"  Published article with ID: {article.id}")

                article_ids = [a.id for a in published_articles]
                first_article_id = article_ids[0] if article_ids else None
                first_qa_scores = all_qa_scores[0] if all_qa_scores else None

                self.logger.info(
                    f"Step 9: Published {len(published_articles)} articles: {article_ids}"
                )

                return ProcessResponse(
                    success=True,
                    article_id=first_article_id,
                    article_ids=article_ids,
                    article_count=len(published_articles),
                    message=f"Successfully created {len(published_articles)} article(s)",
                    qa_scores=first_qa_scores,
                )

            finally:
                await self.facebook_access_agent.close()

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.logger.error(f"Pipeline error: {str(e)}\n{error_details}")
            return ProcessResponse(
                success=False,
                article_id=None,
                article_ids=[],
                article_count=0,
                message=f"Pipeline error: {str(e)}",
                qa_scores=None,
            )
