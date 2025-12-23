import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Loader2, AlertCircle } from 'lucide-react'
import ArticleDetail from '../components/ArticleDetail'
import { getArticle } from '../services/api'
import type { Article as ArticleType } from '../types'
import styles from './Article.module.css'

export default function Article() {
    const { id } = useParams<{ id: string }>()
    const navigate = useNavigate()

    const [article, setArticle] = useState<ArticleType | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        async function fetchArticle() {
            if (!id) {
                setError('Article ID not provided')
                setLoading(false)
                return
            }

            try {
                const data = await getArticle(id)
                setArticle(data)
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Failed to load article')
            } finally {
                setLoading(false)
            }
        }

        fetchArticle()
    }, [id])

    if (loading) {
        return (
            <div className={styles.loadingContainer}>
                <Loader2 size={40} className="spin" />
                <p>Loading article...</p>
            </div>
        )
    }

    if (error || !article) {
        return (
            <div className={styles.errorContainer}>
                <AlertCircle size={48} />
                <h2>Article Not Found</h2>
                <p>{error || 'The requested article could not be found.'}</p>
                <button className="btn btn-primary" onClick={() => navigate('/')}>
                    Back to Home
                </button>
            </div>
        )
    }

    return <ArticleDetail article={article} />
}
