from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class URLType(str, Enum):
    PAGE = "page"
    GROUP = "group"


class ProcessRequest(BaseModel):
    url: str = Field(..., description="Facebook page or group URL")


class PostData(BaseModel):
    post_id: str
    content: str
    author: Optional[str] = None
    timestamp: Optional[datetime] = None
    images: List[str] = []
    reactions: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None


class InputResult(BaseModel):
    url: str
    url_type: URLType
    page_id: str
    is_valid: bool
    error: Optional[str] = None


class CrawlResult(BaseModel):
    posts: List[PostData]
    page_name: Optional[str] = None
    page_description: Optional[str] = None
    total_posts: int


class LanguageInfo(BaseModel):
    language: str
    dialect: Optional[str] = None
    confidence: float


class Entity(BaseModel):
    text: str
    label: str
    start: int
    end: int


class ComprehensionResult(BaseModel):
    post_id: str
    language_info: LanguageInfo
    entities: List[Entity]
    keywords: List[str]
    sentiment: str
    topics: List[str]


class TagResult(BaseModel):
    post_id: str
    categories: List[str]
    tags: List[str]
    importance_score: float


class ArticleSection(BaseModel):
    title: str
    content_sources: List[str]
    order: int


class ArticlePlan(BaseModel):
    title: str
    summary: str
    sections: List[ArticleSection]
    language: str
    dialect: Optional[str] = None


class ArticleContent(BaseModel):
    title: str
    summary: str
    body: str
    sections: Dict[str, str]
    language: str
    dialect: Optional[str] = None


class QAScores(BaseModel):
    readability: float = Field(..., ge=0, le=100)
    coherence: float = Field(..., ge=0, le=100)
    redundancy: float = Field(..., ge=0, le=100)
    neutrality: float = Field(..., ge=0, le=100)
    human_likeness: float = Field(..., ge=0, le=100)
    passed: bool
    failed_metrics: List[str] = []


class Article(BaseModel):
    id: Optional[str] = None
    title: str
    summary: str
    body: str
    language: str
    dialect: Optional[str] = None
    source_url: str
    source_type: URLType
    tags: List[str] = []
    categories: List[str] = []
    qa_scores: Optional[QAScores] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    status: str = "draft"


class ProcessResponse(BaseModel):
    success: bool
    article_id: Optional[str] = None
    article_ids: List[str] = []
    article_count: int = 0
    message: str
    qa_scores: Optional[QAScores] = None


class ArticleListResponse(BaseModel):
    articles: List[Article]
    total: int
    page: int
    page_size: int
