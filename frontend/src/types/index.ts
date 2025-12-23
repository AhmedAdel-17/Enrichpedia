export interface QAScores {
    readability: number;
    coherence: number;
    redundancy: number;
    neutrality: number;
    human_likeness: number;
    passed: boolean;
    failed_metrics: string[];
}

export interface Article {
    id: string;
    title: string;
    summary: string | null;
    body: string;
    language: string;
    dialect: string | null;
    source_url: string;
    source_type: 'page' | 'group';
    tags: string[];
    categories: string[];
    qa_scores: QAScores | null;
    created_at: string | null;
    updated_at: string | null;
    status: string;
}

export interface ArticleListResponse {
    articles: Article[];
    total: number;
    page: number;
    page_size: number;
}

export interface ProcessRequest {
    url: string;
}

export interface ProcessResponse {
    success: boolean;
    article_id: string | null;
    message: string;
    qa_scores: QAScores | null;
}

export interface ProcessingTask {
    task_id: string;
    status: 'processing' | 'completed' | 'failed';
    result: ProcessResponse | null;
    error: string | null;
}
