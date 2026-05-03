import os
from firecrawl import FirecrawlApp

WIKICFP_SEARCH_URL = "http://www.wikicfp.com/cfp/servlet/tool.search?q={query}&b=1"
CORE_SEARCH_URL = (
    "https://portal.core.edu.au/conf-ranks/"
    "?search={acronym}&by=acronym&source=CORE2023&sort=atitle&page=1"
)


def _app() -> FirecrawlApp:
    key = os.environ.get("FIRECRAWL_API_KEY", "")
    return FirecrawlApp(api_key=key)


def scrape_to_markdown(url: str) -> str:
    try:
        result = _app().scrape_url(url, params={"formats": ["markdown"]})
        return result.get("markdown", "")
    except Exception as exc:
        return f"[scrape error: {exc}]"


def fetch_wikicfp(query: str) -> str:
    url = WIKICFP_SEARCH_URL.format(query=query.replace(" ", "+"))
    return scrape_to_markdown(url)


def fetch_core_page(acronym: str) -> str:
    url = CORE_SEARCH_URL.format(acronym=acronym.upper())
    return scrape_to_markdown(url)
