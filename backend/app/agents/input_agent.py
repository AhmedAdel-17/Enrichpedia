import re
from typing import Optional
from urllib.parse import urlparse

from app.agents.base_agent import BaseAgent
from app.models.schemas import InputResult, URLType


class InputAgent(BaseAgent):
    def __init__(self):
        super().__init__("InputAgent")
        self.facebook_patterns = {
            "page": [
                r"facebook\.com/([^/?]+)/?$",
                r"facebook\.com/([^/?]+)/posts",
                r"facebook\.com/pages/[^/]+/(\d+)",
                r"fb\.com/([^/?]+)/?$",
            ],
            "group": [
                r"facebook\.com/groups/([^/?]+)",
                r"fb\.com/groups/([^/?]+)",
            ],
        }

    async def execute(self, url: str) -> InputResult:
        self.log_info(f"Validating URL: {url}")

        url = url.strip()
        if not url:
            return InputResult(
                url=url,
                url_type=URLType.PAGE,
                page_id="",
                is_valid=False,
                error="URL is empty",
            )

        parsed = urlparse(url)
        if not parsed.scheme:
            url = f"https://{url}"
            parsed = urlparse(url)

        if parsed.netloc not in [
            "www.facebook.com",
            "facebook.com",
            "m.facebook.com",
            "fb.com",
            "www.fb.com",
        ]:
            return InputResult(
                url=url,
                url_type=URLType.PAGE,
                page_id="",
                is_valid=False,
                error="Not a valid Facebook domain",
            )

        url_type, page_id = self._extract_page_info(url)

        if not page_id:
            return InputResult(
                url=url,
                url_type=URLType.PAGE,
                page_id="",
                is_valid=False,
                error="Could not extract page or group identifier",
            )

        self.log_info(f"Valid {url_type.value}: {page_id}")

        return InputResult(
            url=url,
            url_type=url_type,
            page_id=page_id,
            is_valid=True,
            error=None,
        )

    def _extract_page_info(self, url: str) -> tuple[URLType, Optional[str]]:
        for pattern in self.facebook_patterns["group"]:
            match = re.search(pattern, url)
            if match:
                return URLType.GROUP, match.group(1)

        for pattern in self.facebook_patterns["page"]:
            match = re.search(pattern, url)
            if match:
                return URLType.PAGE, match.group(1)

        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split("/") if p]
        if path_parts and path_parts[0] not in ["watch", "marketplace", "gaming", "events"]:
            return URLType.PAGE, path_parts[0]

        return URLType.PAGE, None
