import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Sparkles, Search, Menu, X } from 'lucide-react'
import styles from './Header.module.css'

export default function Header() {
    const [searchQuery, setSearchQuery] = useState('')
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
    const navigate = useNavigate()

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault()
        if (searchQuery.trim()) {
            navigate(`/?search=${encodeURIComponent(searchQuery.trim())}`)
        }
    }

    return (
        <header className={styles.header}>
            <div className={`container ${styles.container}`}>
                <Link to="/" className={styles.logo}>
                    <div className={styles.logoIcon}>
                        <Sparkles size={24} />
                    </div>
                    <span className={styles.logoText}>Enrich Media</span>
                </Link>

                <nav className={`${styles.nav} ${mobileMenuOpen ? styles.navOpen : ''}`}>
                    <Link to="/" className={styles.navLink}>Articles</Link>
                    <a href="#process" className={styles.navLink}>Process URL</a>
                </nav>

                <form onSubmit={handleSearch} className={styles.searchForm}>
                    <Search size={18} className={styles.searchIcon} />
                    <input
                        type="text"
                        placeholder="Search articles..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className={styles.searchInput}
                    />
                </form>

                <button
                    className={styles.mobileToggle}
                    onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                    aria-label="Toggle menu"
                >
                    {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
                </button>
            </div>
        </header>
    )
}
