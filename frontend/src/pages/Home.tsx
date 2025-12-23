import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Loader2, Sparkles, AlertCircle, CheckCircle2 } from 'lucide-react'
import ArticleList from '../components/ArticleList'
import { getArticles, searchArticles, processUrl } from '../services/api'
import type { Article, ProcessResponse } from '../types'
import styles from './Home.module.css'

export default function Home() {
    const [searchParams] = useSearchParams()
    const searchQuery = searchParams.get('search') || ''

    const [articles, setArticles] = useState<Article[]>([])
    const [loading, setLoading] = useState(true)
    const [page, setPage] = useState(1)
    const [total, setTotal] = useState(0)
    const pageSize = 12

    const [processUrl_, setProcessUrl] = useState('')
    const [processing, setProcessing] = useState(false)
    const [processResult, setProcessResult] = useState<ProcessResponse | null>(null)
    const [processError, setProcessError] = useState<string | null>(null)

    const fetchArticles = useCallback(async () => {
        setLoading(true)
        try {
            const response = searchQuery
                ? await searchArticles(searchQuery, page, pageSize)
                : await getArticles(page, pageSize)

            setArticles(response.articles)
            setTotal(response.total)
        } catch (error) {
            console.error('Failed to fetch articles:', error)
        } finally {
            setLoading(false)
        }
    }, [page, searchQuery])

    useEffect(() => {
        fetchArticles()
    }, [fetchArticles])

    const handleProcess = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!processUrl_.trim()) return

        setProcessing(true)
        setProcessResult(null)
        setProcessError(null)

        try {
            const result = await processUrl({ url: processUrl_.trim() })
            setProcessResult(result)

            if (result.success) {
                setProcessUrl('')
                fetchArticles()
            }
        } catch (error) {
            setProcessError(error instanceof Error ? error.message : 'Failed to process URL')
        } finally {
            setProcessing(false)
        }
    }

    const totalPages = Math.ceil(total / pageSize)

    return (
        <div className="container">
            <section id="process" className={styles.heroSection}>
                <div className={styles.heroContent}>
                    <h1 className={styles.heroTitle}>
                        Transform Content Into
                        <span className={styles.gradient}> Knowledge</span>
                    </h1>
                    <p className={styles.heroDescription}>
                        Enter a public Facebook page or group URL to generate encyclopedic articles
                        powered by advanced AI analysis
                    </p>
                </div>

                <form onSubmit={handleProcess} className={styles.processForm}>
                    <div className={styles.inputWrapper}>
                        <input
                            type="url"
                            placeholder="https://facebook.com/pagename"
                            value={processUrl_}
                            onChange={(e) => setProcessUrl(e.target.value)}
                            className={styles.urlInput}
                            disabled={processing}
                        />
                        <button
                            type="submit"
                            className={`btn btn-primary ${styles.processButton}`}
                            disabled={processing || !processUrl_.trim()}
                        >
                            {processing ? (
                                <>
                                    <Loader2 size={18} className="spin" />
                                    Processing...
                                </>
                            ) : (
                                <>
                                    <Sparkles size={18} />
                                    Generate Article
                                </>
                            )}
                        </button>
                    </div>

                    {processResult && (
                        <div
                            className={`${styles.resultMessage} ${processResult.success ? styles.success : styles.error
                                }`}
                        >
                            {processResult.success ? (
                                <CheckCircle2 size={18} />
                            ) : (
                                <AlertCircle size={18} />
                            )}
                            {processResult.message}
                        </div>
                    )}

                    {processError && (
                        <div className={`${styles.resultMessage} ${styles.error}`}>
                            <AlertCircle size={18} />
                            {processError}
                        </div>
                    )}
                </form>
            </section>

            <section className={styles.articlesSection}>
                <div className={styles.sectionHeader}>
                    <h2>
                        {searchQuery ? `Search Results for "${searchQuery}"` : 'Recent Articles'}
                    </h2>
                    <span className={styles.articleCount}>{total} articles</span>
                </div>

                <ArticleList articles={articles} loading={loading} />

                {totalPages > 1 && (
                    <div className={styles.pagination}>
                        <button
                            className="btn btn-secondary"
                            onClick={() => setPage((p) => Math.max(1, p - 1))}
                            disabled={page === 1}
                        >
                            Previous
                        </button>

                        <span className={styles.pageInfo}>
                            Page {page} of {totalPages}
                        </span>

                        <button
                            className="btn btn-secondary"
                            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                            disabled={page === totalPages}
                        >
                            Next
                        </button>
                    </div>
                )}
            </section>
        </div>
    )
}
