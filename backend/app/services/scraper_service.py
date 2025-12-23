from typing import List, Optional
from playwright.async_api import async_playwright, Browser, Page

from app.models.schemas import PostData, CrawlResult


class ScraperService:
    def __init__(self):
        self._browser: Optional[Browser] = None
        self._playwright = None

    async def initialize(self) -> None:
        if self._browser:
            return

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],
        )

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def get_page(self, url: str) -> Page:
        await self.initialize()

        context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )

        page = await context.new_page()
        await page.goto(url, wait_until="networkidle", timeout=60000)

        return page

    async def scrape_facebook_page(self, url: str) -> CrawlResult:
        page = await self.get_page(url)

        try:
            posts = await self._extract_posts_from_page(page)
            page_name = await self._get_page_name(page)

            return CrawlResult(
                posts=posts,
                page_name=page_name,
                page_description=None,
                total_posts=len(posts),
            )
        finally:
            await page.close()

    async def _extract_posts_from_page(self, page: Page) -> List[PostData]:
        await self._scroll_to_load_content(page)

        posts_data = await page.evaluate("""
            () => {
                const posts = [];
                const articles = document.querySelectorAll('[role="article"]');
                
                articles.forEach((article, idx) => {
                    const text = article.innerText;
                    if (text && text.length > 50) {
                        const images = [];
                        article.querySelectorAll('img').forEach(img => {
                            if (img.src && img.src.includes('scontent')) {
                                images.push(img.src);
                            }
                        });
                        
                        posts.push({
                            idx: idx,
                            text: text.substring(0, 3000),
                            images: images.slice(0, 3)
                        });
                    }
                });
                
                return posts.slice(0, 50);
            }
        """)

        return [
            PostData(
                post_id=f"post_{item['idx']}",
                content=item["text"],
                author=None,
                timestamp=None,
                images=item.get("images", []),
                reactions=None,
                comments=None,
                shares=None,
            )
            for item in posts_data
        ]

    async def _scroll_to_load_content(self, page: Page, max_scrolls: int = 10) -> None:
        import asyncio

        for _ in range(max_scrolls):
            previous_height = await page.evaluate("document.body.scrollHeight")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            current_height = await page.evaluate("document.body.scrollHeight")

            if current_height == previous_height:
                break

    async def _get_page_name(self, page: Page) -> Optional[str]:
        try:
            return await page.evaluate("""
                () => {
                    const h1 = document.querySelector('h1');
                    return h1 ? h1.innerText : null;
                }
            """)
        except Exception:
            return None
