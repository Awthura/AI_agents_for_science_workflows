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


def _app() -> FirecrawlApp:
    key = os.environ.get("FIRECRAWL_API_KEY", "")
    api_url = os.environ.get("FIRECRAWL_API_URL", "http://localhost:3002")
    return FirecrawlApp(api_key=key, api_url=api_url)


def scrape_to_markdown(url: str, save_dir: str = "") -> str:
    app = _app()
    try:
        result = app.scrape(
            url,
            formats=["markdown"],
            only_main_content=True
        )

        content = result.get("markdown", "") if isinstance(result, dict) else getattr(result, "markdown", "")

        # Minimalistisches Speichern der Markdown-Dateien für das Benchmarking
        if save_dir and content.strip():
            os.makedirs(save_dir, exist_ok=True)
            # URL-Bereinigung für einen gültigen Dateinamen
            clean_name = url.split("://")[-1].replace("/", "_").replace("?", "_").replace("&", "_").replace("=", "_")
            filepath = os.path.join(save_dir, f"{clean_name[:150]}.md")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

        return content

    except Exception as exc:
        # FEHLERBEHANDLUNG:
        # Gib in der Konsole aus, dass die Seite nicht erreichbar war,
        # und gib einen leeren String zurück, damit die Paginierung sofort stoppt.
        print(f"  [!] HTTP/Netzwerk-Fehler bei {url}")
        print(f"      Details: {exc}")
        return ""


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


def fetch_cfplist(query: str, page: int = 1) -> str:
    """
    Scrapt die Suchergebnisseite von cfplist.com für den gegebenen Suchbegriff.
    Nutzt Firecrawl, um den HTML-Inhalt der Ergebnisseite als Markdown zurückzugeben.
    """
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://www.cfplist.com/search?q={encoded_query}&page={page}"

    print(f"Scrape URL: {url}")
    return scrape_to_markdown(url)