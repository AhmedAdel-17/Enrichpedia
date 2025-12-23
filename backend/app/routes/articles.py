from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from app.models.schemas import Article, ArticleListResponse, QAScores, URLType
from app.database import supabase
from app.models.database_models import ARTICLES_TABLE


router = APIRouter()


@router.get("/", response_model=ArticleListResponse)
async def list_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    language: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
):
    offset = (page - 1) * page_size

    query = supabase.table(ARTICLES_TABLE).select("*", count="exact")

    if language:
        query = query.eq("language", language)

    if category:
        query = query.contains("categories", [category])

    if status:
        query = query.eq("status", status)

    query = query.order("created_at", desc=True)
    query = query.range(offset, offset + page_size - 1)

    response = query.execute()

    articles = []
    for row in response.data:
        qa_scores = None
        if row.get("qa_readability") is not None:
            qa_scores = QAScores(
                readability=row.get("qa_readability", 0),
                coherence=row.get("qa_coherence", 0),
                redundancy=row.get("qa_redundancy", 0),
                neutrality=row.get("qa_neutrality", 0),
                human_likeness=row.get("qa_human_likeness", 0),
                passed=row.get("qa_passed", False),
                failed_metrics=[],
            )

        articles.append(
            Article(
                id=row["id"],
                title=row["title"],
                summary=row.get("summary"),
                body=row["body"],
                language=row["language"],
                dialect=row.get("dialect"),
                source_url=row["source_url"],
                source_type=URLType(row["source_type"]),
                tags=row.get("tags", []),
                categories=row.get("categories", []),
                qa_scores=qa_scores,
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
                status=row.get("status", "draft"),
            )
        )

    total = response.count if response.count else len(articles)

    return ArticleListResponse(
        articles=articles,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{article_id}", response_model=Article)
async def get_article(article_id: str):
    response = (
        supabase.table(ARTICLES_TABLE)
        .select("*")
        .eq("id", article_id)
        .single()
        .execute()
    )

    if not response.data:
        raise HTTPException(status_code=404, detail="Article not found")

    row = response.data

    qa_scores = None
    if row.get("qa_readability") is not None:
        qa_scores = QAScores(
            readability=row.get("qa_readability", 0),
            coherence=row.get("qa_coherence", 0),
            redundancy=row.get("qa_redundancy", 0),
            neutrality=row.get("qa_neutrality", 0),
            human_likeness=row.get("qa_human_likeness", 0),
            passed=row.get("qa_passed", False),
            failed_metrics=[],
        )

    return Article(
        id=row["id"],
        title=row["title"],
        summary=row.get("summary"),
        body=row["body"],
        language=row["language"],
        dialect=row.get("dialect"),
        source_url=row["source_url"],
        source_type=URLType(row["source_type"]),
        tags=row.get("tags", []),
        categories=row.get("categories", []),
        qa_scores=qa_scores,
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
        status=row.get("status", "draft"),
    )


@router.delete("/{article_id}")
async def delete_article(article_id: str):
    response = (
        supabase.table(ARTICLES_TABLE)
        .delete()
        .eq("id", article_id)
        .execute()
    )

    if not response.data:
        raise HTTPException(status_code=404, detail="Article not found")

    return {"message": "Article deleted successfully", "id": article_id}


@router.get("/search/")
async def search_articles(
    q: str = Query(..., min_length=2),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    offset = (page - 1) * page_size

    response = (
        supabase.table(ARTICLES_TABLE)
        .select("*", count="exact")
        .or_(f"title.ilike.%{q}%,summary.ilike.%{q}%,body.ilike.%{q}%")
        .order("created_at", desc=True)
        .range(offset, offset + page_size - 1)
        .execute()
    )

    articles = []
    for row in response.data:
        qa_scores = None
        if row.get("qa_readability") is not None:
            qa_scores = QAScores(
                readability=row.get("qa_readability", 0),
                coherence=row.get("qa_coherence", 0),
                redundancy=row.get("qa_redundancy", 0),
                neutrality=row.get("qa_neutrality", 0),
                human_likeness=row.get("qa_human_likeness", 0),
                passed=row.get("qa_passed", False),
                failed_metrics=[],
            )

        articles.append(
            Article(
                id=row["id"],
                title=row["title"],
                summary=row.get("summary"),
                body=row["body"],
                language=row["language"],
                dialect=row.get("dialect"),
                source_url=row["source_url"],
                source_type=URLType(row["source_type"]),
                tags=row.get("tags", []),
                categories=row.get("categories", []),
                qa_scores=qa_scores,
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
                status=row.get("status", "draft"),
            )
        )

    total = response.count if response.count else len(articles)

    return ArticleListResponse(
        articles=articles,
        total=total,
        page=page,
        page_size=page_size,
    )
