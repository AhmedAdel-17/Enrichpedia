import axios from 'axios';
import type { Article, ArticleListResponse, ProcessRequest, ProcessResponse, ProcessingTask } from '../types';

const api = axios.create({
    baseURL: '/api',
    headers: {
        'Content-Type': 'application/json',
    },
});

export async function getArticles(
    page: number = 1,
    pageSize: number = 10,
    language?: string,
    category?: string
): Promise<ArticleListResponse> {
    const params = new URLSearchParams();
    params.append('page', page.toString());
    params.append('page_size', pageSize.toString());
    if (language) params.append('language', language);
    if (category) params.append('category', category);

    const response = await api.get<ArticleListResponse>(`/articles?${params.toString()}`);
    return response.data;
}

export async function getArticle(id: string): Promise<Article> {
    const response = await api.get<Article>(`/articles/${id}`);
    return response.data;
}

export async function deleteArticle(id: string): Promise<void> {
    await api.delete(`/articles/${id}`);
}

export async function searchArticles(
    query: string,
    page: number = 1,
    pageSize: number = 10
): Promise<ArticleListResponse> {
    const params = new URLSearchParams();
    params.append('q', query);
    params.append('page', page.toString());
    params.append('page_size', pageSize.toString());

    const response = await api.get<ArticleListResponse>(`/articles/search/?${params.toString()}`);
    return response.data;
}

export async function processUrl(request: ProcessRequest): Promise<ProcessResponse> {
    const response = await api.post<ProcessResponse>('/process/', request);
    return response.data;
}

export async function processUrlAsync(request: ProcessRequest): Promise<{ task_id: string; status: string }> {
    const response = await api.post<{ task_id: string; status: string }>('/process/async', request);
    return response.data;
}

export async function getProcessingStatus(taskId: string): Promise<ProcessingTask> {
    const response = await api.get<ProcessingTask>(`/process/status/${taskId}`);
    return response.data;
}

export default api;
