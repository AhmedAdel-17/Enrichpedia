# Facebook Access Agent - Uses Apify for data collection
from typing import Dict, Any

from app.agents.base_agent import BaseAgent
from app.models.schemas import InputResult, URLType
from app.services.apify_service import ApifyService


class FacebookAccessAgent(BaseAgent):
    """
    Agent responsible for accessing Facebook content via Apify API.
    Replaces browser-based scraping with Apify actors.
    """
    
    def __init__(self):
        super().__init__("FacebookAccessAgent")
        self.apify_service = ApifyService()
    
    async def execute(self, input_result: InputResult) -> Dict[str, Any]:
        """
        Execute Facebook data collection via Apify.
        
        Args:
            input_result: Validated input containing URL and type
            
        Returns:
            Dict with posts, page_name, page_description, total_posts
        """
        self.log_info(f"Collecting data from {input_result.url_type.value}: {input_result.url}")
        
        try:
            if input_result.url_type == URLType.GROUP:
                result = await self.apify_service.scrape_facebook_group(
                    input_result.url,
                    max_posts=50,
                )
            else:
                result = await self.apify_service.scrape_facebook_page(
                    input_result.url,
                    max_posts=50,
                )
            
            post_count = len(result.get("posts", []))
            self.log_info(f"Collected {post_count} posts from Apify")
            
            return result
            
        except Exception as e:
            self.log_error(f"Apify scraping failed: {str(e)}")
            raise
    
    async def close(self) -> None:
        """Close the Apify service client."""
        await self.apify_service.close()
