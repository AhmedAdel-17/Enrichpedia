import { Link } from 'react-router-dom'
import { Calendar, Globe, Tag, ArrowRight, CheckCircle, XCircle } from 'lucide-react'
import { format } from 'date-fns'
import type { Article } from '../types'
import styles from './ArticleList.module.css'

interface ArticleListProps {
    articles: Article[]
    loading?: boolean
}

export default function ArticleList({ articles, loading }: ArticleListProps) {
    if (loading) {
        return (
            <div className={styles.grid}>
                {[...Array(6)].map((_, i) => (
                    <div key={i} className={styles.skeleton}>
                        <div className={styles.skeletonHeader} />
                        <div className={styles.skeletonTitle} />
                        <div className={styles.skeletonText} />
                        <div className={styles.skeletonText} style={{ width: '60%' }} />
                        <div className={styles.skeletonFooter} />
                    </div>
                ))}
            </div>
        )
    }

    if (articles.length === 0) {
        return (
            <div className={styles.empty}>
                <div className={styles.emptyIcon}>
                    <Globe size={48} />
                </div>
                <h3>No articles yet</h3>
                <p>Process a Facebook URL to create your first article</p>
            </div>
        )
    }

    return (
        <div className={styles.grid}>
            {articles.map((article, index) => (
                <Link
                    key={article.id}
                    to={`/article/${article.id}`}
                    className={styles.card}
                    style={{ animationDelay: `${index * 50}ms` }}
                >
                    <div className={styles.cardHeader}>
                        <div className={styles.badges}>
                            <span className={`badge ${styles.langBadge}`}>
                                {article.language === 'ar' ? 'العربية' : 'English'}
                            </span>
                            {article.qa_scores?.passed && (
                                <span className="badge badge-success">
                                    <CheckCircle size={12} />
                                    Verified
                                </span>
                            )}
                            {article.qa_scores && !article.qa_scores.passed && (
                                <span className="badge badge-warning">
                                    <XCircle size={12} />
                                    Review
                                </span>
                            )}
                        </div>
                        <span className={styles.sourceType}>
                            {article.source_type === 'group' ? 'Group' : 'Page'}
                        </span>
                    </div>

                    <h3 className={styles.title}>{article.title}</h3>

                    {article.summary && (
                        <p className={styles.summary}>
                            {article.summary.length > 150
                                ? `${article.summary.substring(0, 150)}...`
                                : article.summary}
                        </p>
                    )}

                    <div className={styles.tags}>
                        {article.categories.slice(0, 3).map((cat) => (
                            <span key={cat} className="badge badge-accent">
                                <Tag size={10} />
                                {cat}
                            </span>
                        ))}
                    </div>

                    <div className={styles.cardFooter}>
                        <div className={styles.meta}>
                            <Calendar size={14} />
                            <span>
                                {article.created_at
                                    ? format(new Date(article.created_at), 'MMM d, yyyy')
                                    : 'Unknown date'}
                            </span>
                        </div>
                        <span className={styles.readMore}>
                            Read article
                            <ArrowRight size={16} />
                        </span>
                    </div>

                    <div className={styles.cardGlow} />
                </Link>
            ))}
        </div>
    )
}
