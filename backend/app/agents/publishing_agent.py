from typing import List, Optional
from datetime import datetime
import uuid

from app.agents.base_agent import BaseAgent
from app.models.schemas import (
    ArticleContent,
    Article,
    QAScores,
    URLType,
    InputResult,
    TagResult,
)
from app.database import supabase
from app.models.database_models import ARTICLES_TABLE


class PublishingAgent(BaseAgent):
    def __init__(self):
        super().__init__("PublishingAgent")

    async def execute(
        self,
        article_content: ArticleContent,
        input_result: InputResult,
        tag_results: List[TagResult],
        qa_scores: QAScores,
    ) -> Article:
        self.log_info(f"Publishing article: {article_content.title}")

        all_tags = set()
        all_categories = set()
        for tag_result in tag_results:
            all_tags.update(tag_result.tags)
            all_categories.update(tag_result.categories)

        article_id = str(uuid.uuid4())

        article = Article(
            id=article_id,
            title=article_content.title,
            summary=article_content.summary,
            body=article_content.body,
            language=article_content.language,
            dialect=article_content.dialect,
            source_url=input_result.url,
            source_type=input_result.url_type,
            tags=list(all_tags),
            categories=list(all_categories),
            qa_scores=qa_scores,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            status="published",
        )

        await self._save_to_database(article)

        self.log_info(f"Article published with ID: {article_id}")
        return article

    async def _save_to_database(self, article: Article) -> None:
        data = {
            "id": article.id,
            "title": article.title,
            "summary": article.summary,
            "body": article.body,
            "language": article.language,
            "dialect": article.dialect,
            "source_url": article.source_url,
            "source_type": article.source_type.value,
            "tags": article.tags,
            "categories": article.categories,
            "qa_readability": article.qa_scores.readability if article.qa_scores else None,
            "qa_coherence": article.qa_scores.coherence if article.qa_scores else None,
            "qa_redundancy": article.qa_scores.redundancy if article.qa_scores else None,
            "qa_neutrality": article.qa_scores.neutrality if article.qa_scores else None,
            "qa_human_likeness": article.qa_scores.human_likeness if article.qa_scores else None,
            "qa_passed": article.qa_scores.passed if article.qa_scores else False,
            "status": article.status,
            "created_at": article.created_at.isoformat() if article.created_at else None,
            "updated_at": article.updated_at.isoformat() if article.updated_at else None,
        }

        response = supabase.table(ARTICLES_TABLE).insert(data).execute()

        if hasattr(response, "error") and response.error:
            self.log_error(f"Database error: {response.error}")
            raise Exception(f"Failed to save article: {response.error}")

    async def update_article(self, article: Article) -> Article:
        self.log_info(f"Updating article: {article.id}")

        data = {
            "title": article.title,
            "summary": article.summary,
            "body": article.body,
            "qa_readability": article.qa_scores.readability if article.qa_scores else None,
            "qa_coherence": article.qa_scores.coherence if article.qa_scores else None,
            "qa_redundancy": article.qa_scores.redundancy if article.qa_scores else None,
            "qa_neutrality": article.qa_scores.neutrality if article.qa_scores else None,
            "qa_human_likeness": article.qa_scores.human_likeness if article.qa_scores else None,
            "qa_passed": article.qa_scores.passed if article.qa_scores else False,
            "updated_at": datetime.utcnow().isoformat(),
        }

        response = (
            supabase.table(ARTICLES_TABLE)
            .update(data)
            .eq("id", article.id)
            .execute()
        )

        if hasattr(response, "error") and response.error:
            self.log_error(f"Database error: {response.error}")
            raise Exception(f"Failed to update article: {response.error}")

        return article
