import { Link } from 'react-router-dom'
import {
    ArrowLeft,
    Calendar,
    Globe,
    ExternalLink,
    Tag,
    BarChart3,
    CheckCircle,
    XCircle,
} from 'lucide-react'
import { format } from 'date-fns'
import ReactMarkdown from 'react-markdown'
import type { Article } from '../types'
import styles from './ArticleDetail.module.css'

interface ArticleDetailProps {
    article: Article
}

export default function ArticleDetail({ article }: ArticleDetailProps) {
    const isRTL = article.language === 'ar'

    return (
        <article className={styles.article} dir={isRTL ? 'rtl' : 'ltr'}>
            <header className={styles.header}>
                <Link to="/" className={styles.backLink}>
                    <ArrowLeft size={18} />
                    Back to articles
                </Link>

                <div className={styles.meta}>
                    <span className="badge">
                        <Globe size={12} />
                        {article.language === 'ar' ? 'العربية' : 'English'}
                        {article.dialect && ` (${article.dialect})`}
                    </span>
                    <span className={styles.separator}>•</span>
                    <span className={styles.metaItem}>
                        <Calendar size={14} />
                        {article.created_at
                            ? format(new Date(article.created_at), 'MMMM d, yyyy')
                            : 'Unknown date'}
                    </span>
                    <span className={styles.separator}>•</span>
                    <span className={styles.metaItem}>
                        Source: {article.source_type === 'group' ? 'Facebook Group' : 'Facebook Page'}
                    </span>
                </div>

                <h1 className={styles.title}>{article.title}</h1>

                {article.summary && (
                    <p className={styles.summary}>{article.summary}</p>
                )}

                <div className={styles.tags}>
                    {article.categories.map((cat) => (
                        <span key={cat} className="badge badge-accent">
                            <Tag size={10} />
                            {cat}
                        </span>
                    ))}
                    {article.tags.slice(0, 5).map((tag) => (
                        <span key={tag} className="badge">
                            {tag}
                        </span>
                    ))}
                </div>
            </header>

            <div className={styles.content}>
                <ReactMarkdown
                    components={{
                        h1: ({ children }) => <h2 className={styles.h2}>{children}</h2>,
                        h2: ({ children }) => <h2 className={styles.h2}>{children}</h2>,
                        h3: ({ children }) => <h3 className={styles.h3}>{children}</h3>,
                        p: ({ children }) => <p className={styles.paragraph}>{children}</p>,
                        ul: ({ children }) => <ul className={styles.list}>{children}</ul>,
                        ol: ({ children }) => <ol className={styles.list}>{children}</ol>,
                        li: ({ children }) => <li className={styles.listItem}>{children}</li>,
                        blockquote: ({ children }) => (
                            <blockquote className={styles.blockquote}>{children}</blockquote>
                        ),
                        a: ({ href, children }) => (
                            <a href={href} target="_blank" rel="noopener noreferrer">
                                {children}
                            </a>
                        ),
                    }}
                >
                    {article.body}
                </ReactMarkdown>
            </div>

            {article.qa_scores && (
                <aside className={styles.sidebar}>
                    <div className={styles.qaCard}>
                        <div className={styles.qaHeader}>
                            <BarChart3 size={20} />
                            <h4>Quality Scores</h4>
                            {article.qa_scores.passed ? (
                                <span className="badge badge-success">
                                    <CheckCircle size={12} />
                                    Passed
                                </span>
                            ) : (
                                <span className="badge badge-warning">
                                    <XCircle size={12} />
                                    Needs Review
                                </span>
                            )}
                        </div>

                        <div className={styles.scores}>
                            <div className={styles.scoreItem}>
                                <span className={styles.scoreLabel}>Readability</span>
                                <div className={styles.scoreBar}>
                                    <div
                                        className={styles.scoreProgress}
                                        style={{
                                            width: `${article.qa_scores.readability}%`,
                                            backgroundColor: getScoreColor(article.qa_scores.readability),
                                        }}
                                    />
                                </div>
                                <span className={styles.scoreValue}>
                                    {article.qa_scores.readability.toFixed(1)}
                                </span>
                            </div>

                            <div className={styles.scoreItem}>
                                <span className={styles.scoreLabel}>Coherence</span>
                                <div className={styles.scoreBar}>
                                    <div
                                        className={styles.scoreProgress}
                                        style={{
                                            width: `${article.qa_scores.coherence}%`,
                                            backgroundColor: getScoreColor(article.qa_scores.coherence),
                                        }}
                                    />
                                </div>
                                <span className={styles.scoreValue}>
                                    {article.qa_scores.coherence.toFixed(1)}
                                </span>
                            </div>

                            <div className={styles.scoreItem}>
                                <span className={styles.scoreLabel}>Redundancy</span>
                                <div className={styles.scoreBar}>
                                    <div
                                        className={styles.scoreProgress}
                                        style={{
                                            width: `${article.qa_scores.redundancy}%`,
                                            backgroundColor: getScoreColor(100 - article.qa_scores.redundancy),
                                        }}
                                    />
                                </div>
                                <span className={styles.scoreValue}>
                                    {article.qa_scores.redundancy.toFixed(1)}
                                </span>
                            </div>

                            <div className={styles.scoreItem}>
                                <span className={styles.scoreLabel}>Neutrality</span>
                                <div className={styles.scoreBar}>
                                    <div
                                        className={styles.scoreProgress}
                                        style={{
                                            width: `${article.qa_scores.neutrality}%`,
                                            backgroundColor: getScoreColor(article.qa_scores.neutrality),
                                        }}
                                    />
                                </div>
                                <span className={styles.scoreValue}>
                                    {article.qa_scores.neutrality.toFixed(1)}
                                </span>
                            </div>

                            <div className={styles.scoreItem}>
                                <span className={styles.scoreLabel}>Human-likeness</span>
                                <div className={styles.scoreBar}>
                                    <div
                                        className={styles.scoreProgress}
                                        style={{
                                            width: `${article.qa_scores.human_likeness}%`,
                                            backgroundColor: getScoreColor(article.qa_scores.human_likeness),
                                        }}
                                    />
                                </div>
                                <span className={styles.scoreValue}>
                                    {article.qa_scores.human_likeness.toFixed(1)}
                                </span>
                            </div>
                        </div>
                    </div>

                    <a
                        href={article.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={styles.sourceLink}
                    >
                        <ExternalLink size={16} />
                        View Original Source
                    </a>
                </aside>
            )}
        </article>
    )
}

function getScoreColor(score: number): string {
    if (score >= 75) return '#10b981'
    if (score >= 50) return '#f59e0b'
    return '#ef4444'
}
