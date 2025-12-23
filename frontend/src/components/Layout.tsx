import { ReactNode } from 'react'
import Header from './Header'
import styles from './Layout.module.css'

interface LayoutProps {
    children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
    return (
        <div className={styles.layout}>
            <Header />
            <main className={styles.main}>
                {children}
            </main>
            <footer className={styles.footer}>
                <div className="container">
                    <p>Enrich Media - Transform content into knowledge</p>
                </div>
            </footer>
        </div>
    )
}
