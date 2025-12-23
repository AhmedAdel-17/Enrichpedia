# Crawling Agent - Simplified for Apify data
from typing import List, Dict, Any

from app.agents.base_agent import BaseAgent
from app.models.schemas import CrawlResult, PostData, InputResult


class CrawlingAgent(BaseAgent):
    """
    Crawling agent that processes structured data from Apify.
    No longer performs HTML parsing - receives pre-structured data.
    """
    
    def __init__(self):
        super().__init__("CrawlingAgent")

    async def execute(self, scrape_result: Dict[str, Any], input_result: InputResult) -> CrawlResult:
        """
        Process structured Apify data into CrawlResult.
        
        Args:
            scrape_result: Dict from FacebookAccessAgent containing posts and metadata
            input_result: Original input validation result
            
        Returns:
            CrawlResult with normalized posts
        """
        self.log_info("Processing Apify data")
        
        # Extract posts from Apify result
        posts = scrape_result.get("posts", [])
        page_name = scrape_result.get("page_name")
        page_description = scrape_result.get("page_description")
        
        # Ensure posts are PostData objects
        normalized_posts: List[PostData] = []
        for post in posts:
            if isinstance(post, PostData):
                normalized_posts.append(post)
            elif isinstance(post, dict):
                # Convert dict to PostData if needed
                normalized_posts.append(PostData(
                    post_id=post.get("post_id", f"post_{len(normalized_posts)}"),
                    content=post.get("content", ""),
                    author=post.get("author"),
                    timestamp=post.get("timestamp"),
                    images=post.get("images", []),
                    reactions=post.get("reactions"),
                    comments=post.get("comments"),
                    shares=post.get("shares"),
                ))
        
        # Filter out posts with insufficient content
        valid_posts = [p for p in normalized_posts if len(p.content) >= 20]
        
        self.log_info(f"Processed {len(valid_posts)} valid posts")
        
        return CrawlResult(
            posts=valid_posts,
            page_name=page_name,
            page_description=page_description,
            total_posts=len(valid_posts),
        )
