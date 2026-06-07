import os
import urllib.parse
from datetime import datetime
from firecrawl import FirecrawlApp

# Wir fügen Platzhalter für year und page hinzu
WIKICFP_SEARCH_URL = "http://www.wikicfp.com/cfp/servlet/tool.search?q={query}&year={year}&page={page}"
CORE_SEARCH_URL = (
    "https://portal.core.edu.au/conf-ranks/"
    "?search={acronym}&by=acronym&source=CORE2023&sort=atitle&page=1"
)
EASYCHAIR_SEARCH_URL = "https://easychair.org/cfp/search?query={query}"


def _app() -> FirecrawlApp:
    key = os.environ.get("FIRECRAWL_API_KEY", "")
    api_url = os.environ.get("FIRECRAWL_API_URL", "http://localhost:3002")
    return FirecrawlApp(api_key=key, api_url=api_url)


def scrape_to_markdown(url: str) -> str:
    app = _app()
    try:
        # Sauberer Aufruf mit der aktuellen Syntax
        result = app.scrape(
            url,
            formats=["markdown"],
            only_main_content=True
        )

        # Flexibler Check: Ist es ein Dictionary oder ein Objekt?
        if isinstance(result, dict):
            return result.get("markdown", "")
        else:
            # Bei Objekten greifen wir direkt auf das Attribut zu
            return getattr(result, "markdown", "")

    except Exception as exc:
        return f"[scrape error: {exc}]"


def fetch_wikicfp(query: str, page: int = 1, fetch_current_year: bool = True) -> str:
    safe_query = urllib.parse.quote_plus(query)
    # Wenn gewünscht, filtern wir direkt nach dem aktuellen Jahr
    year_param = datetime.now().year if fetch_current_year else ""

    url = WIKICFP_SEARCH_URL.format(query=safe_query, year=year_param, page=page)
    print(f"Scrape URL: {url}")  # Hilfreich fürs Debugging
    return scrape_to_markdown(url)


def fetch_core_page(acronym: str) -> str:
    safe_acronym = urllib.parse.quote_plus(acronym.upper())
    url = CORE_SEARCH_URL.format(acronym=safe_acronym)
    return scrape_to_markdown(url)


def fetch_easychair(query: str) -> str:
    safe_query = urllib.parse.quote_plus(query)
    url = EASYCHAIR_SEARCH_URL.format(query=safe_query)
    print(f"Scrape URL: {url}")
    return scrape_to_markdown(url)