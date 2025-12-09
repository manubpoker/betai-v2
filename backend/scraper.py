"""
BetAI v2 - Main Scraper Module

Scrapes REAL betting data from Betfair using Playwright.

CRITICAL REQUIREMENTS:
- NO mock data generation
- NO fake/random data
- All data comes from actual Betfair pages
- Uses page.evaluate() for DOM extraction
- All records have data_source='real_scrape'
"""

import sqlite3
import time
from datetime import datetime
from typing import Dict, List, Any
from playwright.sync_api import sync_playwright, Page

# Database path
import os
DATABASE = os.path.join(os.path.dirname(__file__), 'betai.db')

# Betfair sport URLs
SPORT_URLS = {
    "football": "https://www.betfair.com/sport/football",
    "tennis": "https://www.betfair.com/sport/tennis",
    "horse-racing": "https://www.betfair.com/sport/horse-racing",
    "basketball": "https://www.betfair.com/sport/basketball",
    "golf": "https://www.betfair.com/sport/golf",
    "cricket": "https://www.betfair.com/sport/cricket",
}


def parse_odds(odds_str: str) -> float:
    """Convert fractional odds string to decimal odds."""
    if not odds_str or odds_str == "-":
        return None

    odds_str = odds_str.strip().upper()

    if odds_str in ('EVS', 'EVENS'):
        return 2.00

    try:
        if "/" in odds_str:
            num, denom = odds_str.split("/")
            return round(float(num) / float(denom) + 1, 2)
        return float(odds_str)
    except (ValueError, ZeroDivisionError):
        return None


def dismiss_cookie_consent(page: Page) -> bool:
    """Dismiss cookie consent dialog if present."""
    selectors = [
        'button#onetrust-accept-btn-handler',
        'button[id*="accept"]',
        'button:has-text("Accept")',
        'button:has-text("Accept All")',
        '.onetrust-close-btn-handler'
    ]

    for selector in selectors:
        try:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                btn.click(timeout=5000)
                time.sleep(1)
                return True
        except:
            pass

    try:
        page.keyboard.press("Escape")
        time.sleep(0.5)
    except:
        pass

    return False


def scrape_sport(page: Page, sport: str, url: str) -> List[Dict[str, Any]]:
    """
    Scrape events for a single sport from Betfair.

    Uses page.evaluate() to extract REAL data from the DOM.
    NO MOCK DATA GENERATION.
    """
    events = []
    timestamp = datetime.utcnow().isoformat() + 'Z'

    try:
        print(f"  Scraping {sport} from {url}...")
        page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(3)

        # Dismiss cookie consent on first load
        dismiss_cookie_consent(page)

        # Scroll to load dynamic content
        for _ in range(5):
            page.keyboard.press("End")
            time.sleep(0.8)

        # Extract events using JavaScript - REAL DATA ONLY
        raw_events = page.evaluate("""
            () => {
                const events = [];
                const processedUrls = new Set();

                // Find competition headers
                const compHeaders = [];
                document.querySelectorAll('a[href*="/c-"]').forEach(link => {
                    const text = link.textContent.trim();
                    if (text && text.length > 3 && text.length < 100 &&
                        !/^[12]$/.test(text) && !text.match(/^\\d+\\//)) {
                        const rect = link.getBoundingClientRect();
                        compHeaders.push({
                            name: text,
                            top: rect.top + window.scrollY
                        });
                    }
                });
                compHeaders.sort((a, b) => a.top - b.top);

                // Find event links (matches/races)
                const eventLinks = document.querySelectorAll('a[href*="/e-"]');

                eventLinks.forEach(link => {
                    const url = link.getAttribute('href');
                    if (processedUrls.has(url)) return;
                    processedUrls.add(url);

                    // Find container with odds
                    let container = link.closest('[class*="generic"], [class*="row"], div');
                    for (let i = 0; i < 8 && container; i++) {
                        const buttons = container.querySelectorAll('button');
                        const oddsButtons = Array.from(buttons).filter(b => {
                            const text = b.textContent.trim();
                            // Match fractional odds or decimal
                            return /^\\d+\\/\\d+$/.test(text) ||
                                   /^\\d+\\.\\d+$/.test(text) ||
                                   text === '-' || text === 'EVS';
                        });

                        if (oddsButtons.length >= 2) {
                            // Extract event name from link text
                            const paragraphs = link.querySelectorAll('p, span');
                            const names = [];
                            paragraphs.forEach(p => {
                                const text = p.textContent.trim();
                                if (text && text.length > 1 && text.length < 80 &&
                                    !text.match(/^\\d+[\\/\\.]/) && text !== '-') {
                                    names.push(text);
                                }
                            });

                            // Also check direct text
                            const linkText = link.textContent.trim();
                            if (linkText && !names.length) {
                                const parts = linkText.split(/\\s+v\\s+|\\s+vs\\s+/i);
                                if (parts.length >= 2) {
                                    names.push(...parts.slice(0, 2).map(p => p.trim()));
                                }
                            }

                            if (names.length >= 1) {
                                // Find competition by position
                                const matchRect = container.getBoundingClientRect();
                                const matchTop = matchRect.top + window.scrollY;
                                let comp = '';
                                for (let j = compHeaders.length - 1; j >= 0; j--) {
                                    if (compHeaders[j].top < matchTop) {
                                        comp = compHeaders[j].name;
                                        break;
                                    }
                                }

                                // Check for live indicator
                                const isLive = container.textContent.includes('LIVE') ||
                                              container.textContent.includes('In-Play') ||
                                              container.querySelector('[class*="live"], [class*="Live"]') !== null;

                                // Extract start time if present
                                let startTime = null;
                                const timeMatch = container.textContent.match(/\\d{1,2}:\\d{2}/);
                                if (timeMatch) {
                                    startTime = timeMatch[0];
                                }

                                // Build event name
                                let eventName = names.slice(0, 2).join(' v ');
                                if (!eventName && linkText) {
                                    eventName = linkText.substring(0, 60);
                                }

                                // Extract odds
                                const odds = [];
                                for (let k = 0; k < oddsButtons.length && k < 6; k++) {
                                    odds.push({
                                        text: oddsButtons[k].textContent.trim(),
                                        index: k
                                    });
                                }

                                events.push({
                                    eventName: eventName,
                                    competition: comp,
                                    url: url,
                                    isLive: isLive,
                                    startTime: startTime,
                                    odds: odds,
                                    names: names
                                });
                            }
                            break;
                        }
                        container = container.parentElement;
                    }
                });

                return events;
            }
        """)

        # Process extracted data
        for raw in raw_events:
            if not raw.get('eventName'):
                continue

            event = {
                "event_name": raw['eventName'],
                "sport": sport,
                "competition": raw.get('competition', ''),
                "start_time": raw.get('startTime'),
                "is_live": 1 if raw.get('isLive') else 0,
                "status": "live" if raw.get('isLive') else "upcoming",
                "source_url": f"https://www.betfair.com{raw['url']}" if raw.get('url') else url,
                "scraped_at": timestamp,
                "data_source": "real_scrape",  # CRITICAL: Always real_scrape
                "odds": []
            }

            # Process odds
            names = raw.get('names', [])
            for i, odd in enumerate(raw.get('odds', [])):
                selection_name = names[i] if i < len(names) else f"Selection {i+1}"
                odds_text = odd.get('text', '-')

                event["odds"].append({
                    "selection_name": selection_name,
                    "back_odds": parse_odds(odds_text),
                    "back_odds_fractional": odds_text,
                    "scraped_at": timestamp
                })

            events.append(event)

        print(f"    Found {len(events)} events for {sport}")

    except Exception as e:
        print(f"    Error scraping {sport}: {e}")

    return events


def save_events_to_db(events: List[Dict[str, Any]]) -> int:
    """
    Save scraped events to database.

    All events MUST have data_source='real_scrape'.
    """
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    saved_count = 0

    for event in events:
        # Verify data_source is real_scrape
        if event.get('data_source') != 'real_scrape':
            print(f"WARNING: Skipping event without real_scrape source: {event.get('event_name')}")
            continue

        try:
            # Insert event
            cursor.execute('''
                INSERT INTO scraped_events
                (sport, competition, event_name, start_time, is_live, status,
                 scraped_at, source_url, data_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event['sport'],
                event.get('competition', ''),
                event['event_name'],
                event.get('start_time'),
                event.get('is_live', 0),
                event.get('status', 'upcoming'),
                event['scraped_at'],
                event['source_url'],
                'real_scrape'  # CRITICAL: Always real_scrape
            ))

            event_id = cursor.lastrowid

            # Insert odds
            for odd in event.get('odds', []):
                cursor.execute('''
                    INSERT INTO scraped_odds
                    (event_id, selection_name, back_odds, back_odds_fractional, scraped_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    event_id,
                    odd.get('selection_name', 'Unknown'),
                    odd.get('back_odds'),
                    odd.get('back_odds_fractional'),
                    odd.get('scraped_at', event['scraped_at'])
                ))

            saved_count += 1

        except Exception as e:
            print(f"Error saving event {event.get('event_name')}: {e}")

    conn.commit()
    conn.close()

    return saved_count


def clear_old_events():
    """Remove events older than 24 hours to keep database clean."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Delete old odds first (foreign key)
    cursor.execute('''
        DELETE FROM scraped_odds
        WHERE event_id IN (
            SELECT id FROM scraped_events
            WHERE datetime(scraped_at) < datetime('now', '-24 hours')
        )
    ''')

    # Delete old events
    cursor.execute('''
        DELETE FROM scraped_events
        WHERE datetime(scraped_at) < datetime('now', '-24 hours')
    ''')

    conn.commit()
    conn.close()


def run_full_scrape() -> Dict[str, Any]:
    """
    Run a full scrape of all sports.

    Returns:
        Dict with:
            - total: Total events scraped
            - counts: Events per sport
    """
    print(f"[{datetime.utcnow().isoformat()}] Starting full Betfair scrape...")

    # Clear old data
    clear_old_events()

    counts = {}
    total = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for sport, url in SPORT_URLS.items():
            try:
                events = scrape_sport(page, sport, url)
                saved = save_events_to_db(events)
                counts[sport] = saved
                total += saved
                time.sleep(1)  # Be nice to Betfair
            except Exception as e:
                print(f"Error with {sport}: {e}")
                counts[sport] = 0

        browser.close()

    print(f"Scrape complete. Total events: {total}")
    return {"total": total, "counts": counts}


if __name__ == "__main__":
    # Run scrape when called directly
    result = run_full_scrape()
    print(f"Results: {result}")
