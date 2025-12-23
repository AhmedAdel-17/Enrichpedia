from typing import Optional
from datetime import datetime


ARTICLES_TABLE = "articles"
POSTS_TABLE = "posts"
IMAGES_BUCKET = "article-images"


ARTICLES_SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    summary TEXT,
    body TEXT NOT NULL,
    language VARCHAR(10) NOT NULL,
    dialect VARCHAR(50),
    source_url TEXT NOT NULL,
    source_type VARCHAR(20) NOT NULL,
    tags TEXT[],
    categories TEXT[],
    qa_readability FLOAT,
    qa_coherence FLOAT,
    qa_redundancy FLOAT,
    qa_neutrality FLOAT,
    qa_human_likeness FLOAT,
    qa_passed BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'draft',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
"""

POSTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    post_id TEXT NOT NULL,
    content TEXT,
    author TEXT,
    timestamp TIMESTAMP WITH TIME ZONE,
    images TEXT[],
    reactions INTEGER,
    comments INTEGER,
    shares INTEGER,
    language VARCHAR(10),
    dialect VARCHAR(50),
    entities JSONB,
    keywords TEXT[],
    sentiment VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
"""
