"""
Base Scraper for Betfair

Uses Playwright (NOT Puppeteer) for browser automation.
Extracts REAL data from Betfair pages - NO MOCK DATA GENERATION.
"""

import time
from datetime import datetime
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from typing import Optional, List, Dict, Any


def parse_odds(odds_str: str) -> Optional[float]:
    """
    Convert fractional odds string to decimal odds.

    Examples:
        '5/1' -> 6.00
        '1/4' -> 1.25
        '1/1' or 'EVS' -> 2.00
    """
    if not odds_str or odds_str == "-":
        return None

    odds_str = odds_str.strip().upper()

    # Handle EVS (evens)
    if odds_str in ('EVS', 'EVENS'):
        return 2.00

    try:
        if "/" in odds_str:
            num, denom = odds_str.split("/")
            return round(float(num) / float(denom) + 1, 2)
        return float(odds_str)
    except (ValueError, ZeroDivisionError):
        return None


class BetfairBaseScraper:
    """
    Base class for Betfair scrapers using Playwright.

    CRITICAL REQUIREMENTS:
    - Uses Playwright with headless Chromium
    - Extracts REAL data via page.evaluate()
    - NO mock/fake data generation
    - All records include scraped_at timestamp
    - All records include source_url
    - data_source is always 'real_scrape'
    """

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.playwright = None

    def launch(self) -> Page:
        """
        Launch browser and return a new page.

        Returns:
            Playwright Page object
        """
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu'
            ]
        )
        self.context = self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        return self.context.new_page()

    def dismiss_cookie_consent(self, page: Page) -> bool:
        """
        Dismiss Betfair cookie consent dialog if present.

        Tries multiple selectors as fallback.

        Args:
            page: Playwright page object

        Returns:
            True if consent was dismissed, False otherwise
        """
        selectors = [
            'button#onetrust-accept-btn-handler',
            'button[id*="accept"]',
            'button:has-text("Accept")',
            'button:has-text("Accept All")',
            'button:has-text("Accept Cookies")',
            '.onetrust-close-btn-handler',
            '[aria-label*="accept"]',
            '[aria-label*="Accept"]',
        ]

        for selector in selectors:
            try:
                btn = page.query_selector(selector)
                if btn and btn.is_visible():
                    btn.click(timeout=5000)
                    time.sleep(1)
                    print(f"Cookie consent dismissed with: {selector}")
                    return True
            except Exception:
                pass

        # Also try pressing Escape to close any modal
        try:
            page.keyboard.press("Escape")
            time.sleep(0.5)
        except Exception:
            pass

        return False

    def scroll_page(self, page: Page, times: int = 5, delay: float = 1.0):
        """
        Scroll page to load dynamic content.

        Args:
            page: Playwright page object
            times: Number of times to scroll
            delay: Delay between scrolls in seconds
        """
        for _ in range(times):
            page.keyboard.press("End")
            time.sleep(delay)

    def get_timestamp(self) -> str:
        """Get current UTC timestamp in ISO format."""
        return datetime.utcnow().isoformat() + 'Z'

    def close(self):
        """Clean up browser resources."""
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            print(f"Error closing browser: {e}")

    def scrape(self) -> List[Dict[str, Any]]:
        """
        Override this method in subclasses to implement sport-specific scraping.

        Returns:
            List of event dictionaries with:
                - event_name: str
                - competition: str
                - sport: str
                - start_time: str (optional)
                - is_live: bool
                - source_url: str
                - scraped_at: str (ISO timestamp)
                - data_source: 'real_scrape' (ALWAYS)
                - odds: list of selection dicts
        """
        raise NotImplementedError("Subclasses must implement scrape()")


class EventData:
    """
    Data class for scraped event data.

    Ensures all required fields are present and data_source is always 'real_scrape'.
    """

    def __init__(
        self,
        event_name: str,
        sport: str,
        source_url: str,
        competition: str = "",
        start_time: str = None,
        is_live: bool = False,
        status: str = "upcoming",
        odds: List[Dict] = None
    ):
        self.event_name = event_name
        self.sport = sport
        self.source_url = source_url
        self.competition = competition
        self.start_time = start_time
        self.is_live = is_live
        self.status = status
        self.odds = odds or []
        self.scraped_at = datetime.utcnow().isoformat() + 'Z'
        self.data_source = "real_scrape"  # ALWAYS real_scrape, NEVER mock

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "event_name": self.event_name,
            "sport": self.sport,
            "competition": self.competition,
            "start_time": self.start_time,
            "is_live": 1 if self.is_live else 0,
            "status": self.status,
            "source_url": self.source_url,
            "scraped_at": self.scraped_at,
            "data_source": self.data_source,  # MUST be 'real_scrape'
            "odds": self.odds
        }


class OddsData:
    """Data class for scraped odds."""

    def __init__(
        self,
        selection_name: str,
        back_odds: float = None,
        lay_odds: float = None,
        back_odds_fractional: str = None,
        lay_odds_fractional: str = None,
        liquidity: float = None
    ):
        self.selection_name = selection_name
        self.back_odds = back_odds
        self.lay_odds = lay_odds
        self.back_odds_fractional = back_odds_fractional
        self.lay_odds_fractional = lay_odds_fractional
        self.liquidity = liquidity
        self.scraped_at = datetime.utcnow().isoformat() + 'Z'

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "selection_name": self.selection_name,
            "back_odds": self.back_odds,
            "lay_odds": self.lay_odds,
            "back_odds_fractional": self.back_odds_fractional,
            "lay_odds_fractional": self.lay_odds_fractional,
            "liquidity": self.liquidity,
            "scraped_at": self.scraped_at
        }
