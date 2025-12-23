# Apify Service for Facebook Data Collection
import os
import asyncio
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.models.schemas import PostData
from app.config import settings


class ApifyService:
    """
    Apify REST API client for Facebook scraping.
    Uses official Apify actors for Facebook Pages and Groups.
    """
    
    FACEBOOK_POSTS_ACTOR = "apify~facebook-posts-scraper"
    FACEBOOK_GROUPS_ACTOR = "apify~facebook-groups-scraper"
    
    BASE_URL = "https://api.apify.com/v2"
    
    def __init__(self):
        self.api_token = settings.apify_api_token
        if not self.api_token:
            raise ValueError("APIFY_API_TOKEN environment variable not set")
        self._client: Optional[httpx.AsyncClient] = None

    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=300.0)
        return self._client
    
    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def scrape_facebook_page(self, page_url: str, max_posts: int = 50) -> Dict[str, Any]:
        """
        Scrape a public Facebook page using Apify actor.
        Returns dict with posts, page_name, page_description.
        """
        actor_input = {
            "startUrls": [{"url": page_url}],
            "maxPosts": max_posts,
            "resultsLimit": max_posts,  # Explicitly set results limit
            "view": "latest",           # Force latest posts
            "maxPostComments": 10,
            "maxReviewComments": 0,
            "scrapeAbout": True,
            "scrapePosts": True,
            "scrapeReviews": False,
        }
        
        return await self._run_actor(self.FACEBOOK_POSTS_ACTOR, actor_input)
    
    async def scrape_facebook_group(self, group_url: str, max_posts: int = 50) -> Dict[str, Any]:
        """
        Scrape a public Facebook group using Apify actor.
        Returns dict with posts, group_name, group_description.
        """
        actor_input = {
            "startUrls": [{"url": group_url}],
            "maxPosts": max_posts,
            "resultsLimit": max_posts,
            "maxComments": 10,
        }
        
        return await self._run_actor(self.FACEBOOK_GROUPS_ACTOR, actor_input)
    
    async def _run_actor(self, actor_id: str, actor_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run an Apify actor and wait for results.
        """
        client = await self._get_client()
        
        # Start the actor run
        run_url = f"{self.BASE_URL}/acts/{actor_id}/runs"
        params = {"token": self.api_token}
        
        response = await client.post(
            run_url,
            params=params,
            json=actor_input,
        )
        response.raise_for_status()
        run_data = response.json()
        run_id = run_data["data"]["id"]
        
        # Wait for the run to complete
        status_url = f"{self.BASE_URL}/actor-runs/{run_id}"
        max_wait = 300  # 5 minutes max
        waited = 0
        poll_interval = 5
        
        while waited < max_wait:
            response = await client.get(status_url, params=params)
            response.raise_for_status()
            status_data = response.json()
            status = status_data["data"]["status"]
            
            if status == "SUCCEEDED":
                break
            elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                raise RuntimeError(f"Apify actor run failed with status: {status}")
            
            await asyncio.sleep(poll_interval)
            waited += poll_interval
        
        if waited >= max_wait:
            raise TimeoutError("Apify actor run timed out")
        
        # Get the dataset items
        dataset_id = status_data["data"]["defaultDatasetId"]
        dataset_url = f"{self.BASE_URL}/datasets/{dataset_id}/items"
        
        response = await client.get(dataset_url, params=params)
        response.raise_for_status()
        items = response.json()
        
        return self._normalize_results(items)
    
    def _normalize_results(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Normalize Apify results to match existing schema.
        """
        posts: List[PostData] = []
        page_name: Optional[str] = None
        page_description: Optional[str] = None
        
        for idx, item in enumerate(items):
            # Extract page info from first item
            if idx == 0:
                page_name = item.get("pageName") or item.get("groupName")
                page_description = item.get("about") or item.get("description")
            
            # Handle both page posts and group posts format
            post_text = item.get("text") or item.get("message") or ""
            
            if not post_text or len(post_text) < 10:
                continue
            
            # Parse timestamp
            timestamp = None
            time_str = item.get("time") or item.get("timestamp") or item.get("date")
            if time_str:
                try:
                    if isinstance(time_str, str):
                        # Try multiple formats
                        for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"]:
                            try:
                                timestamp = datetime.strptime(time_str, fmt)
                                break
                            except ValueError:
                                continue
                except Exception:
                    pass
            
            # Extract media URLs
            images = []
            media = item.get("media") or item.get("images") or []
            if isinstance(media, list):
                for m in media:
                    if isinstance(m, dict):
                        url = m.get("url") or m.get("src")
                        if url:
                            images.append(url)
                    elif isinstance(m, str):
                        images.append(m)
            
            # Extract engagement metrics
            reactions = item.get("likes") or item.get("reactions") or item.get("likesCount")
            comments_count = item.get("comments") or item.get("commentsCount")
            shares = item.get("shares") or item.get("sharesCount")
            
            # Extract author
            author = item.get("authorName") or item.get("userName") or page_name
            
            # Extract comments text for additional context
            comments_list = item.get("topComments") or item.get("latestComments") or []
            comment_texts = []
            for comment in comments_list[:5]:
                if isinstance(comment, dict):
                    comment_text = comment.get("text") or comment.get("message")
                    if comment_text:
                        comment_texts.append(comment_text)
            
            # Create post ID from URL or index
            post_url = item.get("url") or item.get("postUrl") or ""
            post_id = f"post_{idx}_{hash(post_url) % 100000}" if post_url else f"post_{idx}"
            
            # Append comment context to post content
            full_content = post_text
            if comment_texts:
                full_content += "\n\n[Comments]:\n" + "\n".join(comment_texts[:3])
            
            posts.append(PostData(
                post_id=post_id,
                content=full_content[:5000],
                author=author,
                timestamp=timestamp,
                images=images[:5],
                reactions=reactions if isinstance(reactions, int) else None,
                comments=comments_count if isinstance(comments_count, int) else None,
                shares=shares if isinstance(shares, int) else None,
            ))
        
        return {
            "posts": posts,
            "page_name": page_name,
            "page_description": page_description,
            "total_posts": len(posts),
        }
