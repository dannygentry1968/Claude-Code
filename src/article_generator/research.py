"""Web research module for gathering article sources."""

import re
from dataclasses import dataclass, field
from urllib.parse import quote_plus, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


@dataclass
class ResearchSource:
    """A research source with extracted content."""

    url: str
    title: str
    content: str
    snippet: str = ""

    def to_context(self) -> str:
        """Format the source for AI context."""
        return f"""Source: {self.title}
URL: {self.url}

{self.content[:3000]}
"""


@dataclass
class ResearchResult:
    """Result of a research query."""

    query: str
    sources: list[ResearchSource] = field(default_factory=list)
    error: str | None = None

    def to_context(self) -> str:
        """Format all sources for AI context."""
        if not self.sources:
            return f"No sources found for query: {self.query}"

        parts = [f"Research Results for: {self.query}\n"]
        for i, source in enumerate(self.sources, 1):
            parts.append(f"--- Source {i} ---")
            parts.append(source.to_context())
            parts.append("")

        return "\n".join(parts)


class WebResearcher:
    """Web research tool for gathering information on topics."""

    def __init__(
        self,
        max_sources: int = 5,
        timeout: float = 30.0,
        user_agent: str | None = None,
    ):
        """Initialize the web researcher.

        Args:
            max_sources: Maximum number of sources to fetch per query.
            timeout: Request timeout in seconds.
            user_agent: Custom user agent string.
        """
        self.max_sources = max_sources
        self.timeout = timeout
        self.user_agent = user_agent or (
            "Mozilla/5.0 (compatible; ArticleResearchBot/1.0; "
            "+https://github.com/example/article-generator)"
        )

    async def research_topic(
        self,
        topic: str,
        additional_queries: list[str] | None = None,
    ) -> list[ResearchResult]:
        """Research a topic by searching and extracting content.

        Args:
            topic: The main topic to research.
            additional_queries: Optional additional search queries.

        Returns:
            List of ResearchResult objects with sources.
        """
        queries = [topic]
        if additional_queries:
            queries.extend(additional_queries)

        results = []
        async with httpx.AsyncClient(
            timeout=self.timeout,
            headers={"User-Agent": self.user_agent},
            follow_redirects=True,
        ) as client:
            for query in queries:
                result = await self._search_and_extract(client, query)
                results.append(result)

        return results

    async def _search_and_extract(
        self,
        client: httpx.AsyncClient,
        query: str,
    ) -> ResearchResult:
        """Search for a query and extract content from results.

        Uses DuckDuckGo HTML search (no API key required).
        """
        result = ResearchResult(query=query)

        try:
            # Use DuckDuckGo HTML search
            search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            response = await client.get(search_url)
            response.raise_for_status()

            # Parse search results
            soup = BeautifulSoup(response.text, "html.parser")
            links = soup.select(".result__a")

            urls_fetched = 0
            for link in links:
                if urls_fetched >= self.max_sources:
                    break

                href = link.get("href")
                title = link.get_text(strip=True)

                if not href or not title:
                    continue

                # Extract actual URL from DuckDuckGo redirect
                url = self._extract_url(href)
                if not url or not self._is_valid_url(url):
                    continue

                # Fetch and extract content
                source = await self._fetch_source(client, url, title)
                if source:
                    result.sources.append(source)
                    urls_fetched += 1

        except httpx.HTTPError as e:
            result.error = f"Search failed: {str(e)}"
        except Exception as e:
            result.error = f"Research error: {str(e)}"

        return result

    def _extract_url(self, href: str) -> str | None:
        """Extract the actual URL from a DuckDuckGo redirect link."""
        # DuckDuckGo uses redirects like //duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com
        if "uddg=" in href:
            from urllib.parse import parse_qs, urlparse

            parsed = urlparse(href)
            params = parse_qs(parsed.query)
            if "uddg" in params:
                return params["uddg"][0]

        # Direct link
        if href.startswith("http"):
            return href

        return None

    def _is_valid_url(self, url: str) -> bool:
        """Check if a URL is valid for content extraction."""
        try:
            parsed = urlparse(url)
            # Skip non-http URLs
            if parsed.scheme not in ("http", "https"):
                return False
            # Skip known problematic domains
            skip_domains = [
                "youtube.com",
                "twitter.com",
                "x.com",
                "facebook.com",
                "instagram.com",
                "tiktok.com",
                "reddit.com",
            ]
            return not any(d in parsed.netloc for d in skip_domains)
        except Exception:
            return False

    async def _fetch_source(
        self,
        client: httpx.AsyncClient,
        url: str,
        title: str,
    ) -> ResearchSource | None:
        """Fetch and extract content from a URL."""
        try:
            response = await client.get(url, timeout=15.0)
            response.raise_for_status()

            # Parse HTML and extract main content
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script, style, and nav elements
            for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
                element.decompose()

            # Try to find main content
            main_content = (
                soup.find("main")
                or soup.find("article")
                or soup.find(class_=re.compile(r"content|article|post", re.I))
                or soup.find("body")
            )

            if not main_content:
                return None

            # Extract text
            text = main_content.get_text(separator="\n", strip=True)

            # Clean up text
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            content = "\n".join(lines)

            # Skip if content is too short
            if len(content) < 200:
                return None

            # Get meta description for snippet
            meta_desc = soup.find("meta", attrs={"name": "description"})
            snippet = meta_desc.get("content", "") if meta_desc else content[:200]

            # Use page title if link title is generic
            page_title = soup.find("title")
            if page_title and len(title) < 10:
                title = page_title.get_text(strip=True)

            return ResearchSource(
                url=url,
                title=title,
                content=content,
                snippet=snippet,
            )

        except Exception:
            return None

    async def fetch_url(self, url: str) -> ResearchSource | None:
        """Fetch content from a specific URL.

        Args:
            url: The URL to fetch.

        Returns:
            ResearchSource or None if fetch fails.
        """
        async with httpx.AsyncClient(
            timeout=self.timeout,
            headers={"User-Agent": self.user_agent},
            follow_redirects=True,
        ) as client:
            return await self._fetch_source(client, url, "")
