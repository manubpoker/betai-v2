"""
BetAI v2 - Sportsbook Scraper Module

Scrapes REAL SPORTSBOOK betting data from Betfair Sportsbook using Playwright.
Sportsbook URLs: betfair.com/sport/{sport} (fixed odds, single price)

Key differences from Exchange:
- Sportsbook has FIXED odds (no back/lay)
- Odds are fractional format
- No user-to-user betting - house takes bets

CRITICAL REQUIREMENTS:
- NO mock data generation
- NO fake/random data
- All data comes from actual Betfair Sportsbook pages
- Uses page.evaluate() for DOM extraction
- All records have data_source='real_scrape' and data_type='sportsbook'
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


def normalize_name(name: str) -> str:
    """
    Normalize event/team names for consistent display.
    Handles case inconsistency (e.g., "Miami Heat" vs "Miami heat").
    """
    if not name:
        return name

    # Title case each word, but preserve certain patterns
    words = name.strip().split()
    normalized = []

    for word in words:
        # Keep "vs" and "v" lowercase
        if word.lower() in ('vs', 'v', 'vs.'):
            normalized.append('v')
        # Keep common abbreviations uppercase
        elif word.upper() in ('FC', 'AFC', 'NBA', 'NFL', 'MLB', 'NHL', 'USA', 'UK', 'II', 'III', 'IV'):
            normalized.append(word.upper())
        # Title case normal words
        else:
            normalized.append(word.capitalize())

    return ' '.join(normalized)


def create_event_key(event_name: str, sport: str, url: str) -> str:
    """
    Create a unique key for deduplication.
    Uses URL as primary key since it's unique per event.
    """
    # URL is the most reliable unique identifier
    if url:
        return url.lower()
    # Fallback to name + sport
    return f"{event_name.lower()}:{sport.lower()}"


def extract_event_name_from_url(url: str, sport: str) -> str:
    """
    Extract event name from Betfair URL.
    URLs contain the actual event name like: miami-heat-%40-orlando-magic/e-35011353
    """
    import re
    from urllib.parse import unquote

    if not url:
        return None

    # Decode URL encoding (%40 -> @, etc.)
    url = unquote(url)

    # Extract the event slug from URL
    # Pattern: /competition-name/event-slug/e-12345 (may have query string after)
    match = re.search(r'/([^/]+)/e-\d+', url)
    if not match:
        return None

    slug = match.group(1)

    # Replace hyphens with spaces
    name = slug.replace('-', ' ')

    # Handle @ symbol (away games)
    name = re.sub(r'\s*@\s*', ' @ ', name)

    # Handle 'v' separator
    name = re.sub(r'\s+v\s+', ' v ', name)

    # Apply normalization
    return normalize_name(name)


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
    seen_keys = set()  # For deduplication
    timestamp = datetime.utcnow().isoformat() + 'Z'

    try:
        print(f"  Scraping {sport} from {url}...", flush=True)
        page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(3)

        # Debug: Check page title and content length
        title = page.title()
        content_len = len(page.content())
        print(f"    Page title: {title}, content length: {content_len}", flush=True)

        # Dismiss cookie consent on first load
        dismiss_cookie_consent(page)

        # Scroll to load dynamic content
        for _ in range(5):
            page.keyboard.press("End")
            time.sleep(0.8)

        # Sport-specific extraction for golf and horse racing
        is_racing = sport in ('horse-racing', 'golf')

        # For golf and horse racing, use a different extraction method
        if is_racing:
            raw_events = page.evaluate("""
                (sport) => {
                    const events = [];

                    // Find tournament/race name from page
                    let tournamentName = '';
                    const headers = document.querySelectorAll('h1, h2, [class*="header"], [class*="title"]');
                    for (const h of headers) {
                        const text = h.textContent.trim();
                        if (text && text.length > 5 && text.length < 100 &&
                            !text.match(/^\\d+/) && !text.includes('Betfair')) {
                            tournamentName = text;
                            break;
                        }
                    }

                    // For golf/racing, extract individual competitors with odds
                    // Find all rows that have odds buttons
                    const allRows = document.querySelectorAll('div, tr, li');
                    const processedNames = new Set();

                    allRows.forEach(row => {
                        // Must have at least one odds button
                        const buttons = row.querySelectorAll('button');
                        const oddsButtons = Array.from(buttons).filter(b => {
                            const text = b.textContent.trim();
                            return /^\\d+\\/\\d+$/.test(text) || text === 'EVS';
                        });

                        if (oddsButtons.length >= 1 && oddsButtons.length <= 6) {
                            // Find competitor name - usually before the odds
                            let competitorName = '';
                            const textNodes = [];

                            // Look for text content before the odds
                            row.querySelectorAll('p, span, a').forEach(el => {
                                const text = el.textContent.trim();
                                // Exclude odds text
                                if (text && text.length > 2 && text.length < 60 &&
                                    !/^\\d+[\\/\\.]/.test(text) && text !== '-' &&
                                    !/^\\d+$/.test(text) && !text.includes('Places EW')) {
                                    textNodes.push(text);
                                }
                            });

                            // Get the first meaningful name
                            if (textNodes.length > 0) {
                                competitorName = textNodes[0];
                            }

                            // Skip if no name or already processed
                            if (!competitorName || processedNames.has(competitorName.toLowerCase())) {
                                return;
                            }
                            processedNames.add(competitorName.toLowerCase());

                            // Skip navigation/header text
                            if (competitorName.toLowerCase().includes('a - z') ||
                                competitorName.toLowerCase().includes('places ew')) {
                                return;
                            }

                            // Extract odds
                            const odds = [];
                            for (let k = 0; k < oddsButtons.length && k < 3; k++) {
                                odds.push({
                                    text: oddsButtons[k].textContent.trim(),
                                    index: k
                                });
                            }

                            events.push({
                                eventName: competitorName,
                                competition: tournamentName,
                                url: window.location.pathname,
                                isLive: false,
                                startTime: null,
                                odds: odds,
                                names: [competitorName]
                            });
                        }
                    });

                    return events;
                }
            """, sport)
        else:
            # Standard extraction for team sports - REAL DATA ONLY
            raw_events = page.evaluate("""
            (isRacing) => {
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

                        // For racing/golf, we might have fewer odds visible
                        const minOdds = isRacing ? 1 : 2;

                        if (oddsButtons.length >= minOdds) {
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
                                // For racing/golf, the event name might be a single entity (race/tournament name)
                                if (isRacing) {
                                    names.push(linkText.trim());
                                } else {
                                    const parts = linkText.split(/\\s+v\\s+|\\s+vs\\s+/i);
                                    if (parts.length >= 2) {
                                        names.push(...parts.slice(0, 2).map(p => p.trim()));
                                    } else {
                                        names.push(linkText.trim());
                                    }
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

                                // Build event name - handle racing/golf differently
                                let eventName;
                                if (isRacing) {
                                    // For racing/golf, use the full name or first name
                                    eventName = names[0] || linkText.substring(0, 60);
                                } else {
                                    // For team sports, join with 'v'
                                    eventName = names.slice(0, 2).join(' v ');
                                    if (!eventName && linkText) {
                                        eventName = linkText.substring(0, 60);
                                    }
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
        """, False)  # is_racing=False for team sports

        # Process extracted data with deduplication
        for raw in raw_events:
            raw_url = raw.get('url', '')

            # Build source URL
            source_url = f"https://www.betfair.com{raw_url}" if raw_url else url

            # Extract event name from URL first (most reliable)
            url_name = extract_event_name_from_url(raw_url, sport)

            # Use URL-extracted name, fallback to JS-extracted name
            if url_name:
                normalized_name = url_name
            elif raw.get('eventName'):
                normalized_name = normalize_name(raw['eventName'])
            else:
                continue  # Skip if no name available

            # Create deduplication key
            # For racing/golf, use name+sport as key since URL is same for all competitors
            if is_racing:
                event_key = f"{normalized_name.lower()}:{sport.lower()}"
            else:
                event_key = create_event_key(normalized_name, sport, source_url)

            # Skip duplicates
            if event_key in seen_keys:
                continue
            seen_keys.add(event_key)

            event = {
                "event_name": normalized_name,
                "sport": sport,
                "competition": raw.get('competition', ''),
                "start_time": raw.get('startTime'),
                "is_live": 1 if raw.get('isLive') else 0,
                "status": "live" if raw.get('isLive') else "upcoming",
                "source_url": source_url,
                "scraped_at": timestamp,
                "data_source": "real_scrape",  # CRITICAL: Always real_scrape
                "data_type": "sportsbook",  # CRITICAL: Mark as sportsbook data
                "odds": []
            }

            # Process odds with normalized selection names
            names = raw.get('names', [])
            odds_list = raw.get('odds', [])

            # For football/soccer with 3 odds (home/draw/away), detect draw position
            is_three_way = (sport == 'football' and len(odds_list) == 3)

            # For two-way bets (basketball, tennis, etc.), detect 2-way markets
            is_two_way = (sport != 'football' and len(odds_list) == 2)

            # Extract team names from the event name
            # Supports "Team A v Team B" and "Team A @ Team B" formats
            home_team = None
            away_team = None
            if ' v ' in normalized_name:
                parts = normalized_name.split(' v ', 1)
                if len(parts) == 2:
                    home_team = parts[0].strip()
                    away_team = parts[1].strip()
            elif ' @ ' in normalized_name:
                # "Away @ Home" format - swap order so away is first, home is second
                parts = normalized_name.split(' @ ', 1)
                if len(parts) == 2:
                    away_team = parts[0].strip()  # First team is away
                    home_team = parts[1].strip()  # Second team is home

            for i, odd in enumerate(odds_list):
                if is_three_way and home_team and away_team:
                    # Football: [Home Win, Draw, Away Win]
                    if i == 0:
                        raw_selection = home_team
                    elif i == 1:
                        raw_selection = "Draw"
                    else:
                        raw_selection = away_team
                elif is_three_way:
                    # Fallback if we couldn't parse team names
                    if i == 0:
                        raw_selection = names[0] if len(names) > 0 else "Home"
                    elif i == 1:
                        raw_selection = "Draw"
                    else:
                        raw_selection = names[1] if len(names) > 1 else (names[0] if len(names) > 0 else "Away")
                elif is_two_way and (home_team or away_team):
                    # Basketball/Tennis: [Away Win, Home Win] or [Home Win, Away Win]
                    # Use the team names from event name parsing
                    if ' @ ' in normalized_name:
                        # "Away @ Home" format: first odds = away, second = home
                        raw_selection = away_team if i == 0 else home_team
                    else:
                        # "Home v Away" format: first odds = home, second = away
                        raw_selection = home_team if i == 0 else away_team
                else:
                    # Fallback: try to use unique names from the JS extraction
                    # Deduplicate names array first
                    unique_names = []
                    for n in names:
                        if n and n not in unique_names:
                            unique_names.append(n)
                    raw_selection = unique_names[i] if i < len(unique_names) else f"Selection {i+1}"

                selection_name = normalize_name(raw_selection)
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
    Save scraped sportsbook events to database.

    All events MUST have:
    - data_source='real_scrape'
    - data_type='sportsbook'
    Uses INSERT OR REPLACE to handle duplicates based on source_url and data_type.
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
            # Check if event already exists by source_url and data_type
            cursor.execute(
                'SELECT id FROM scraped_events WHERE source_url = ? AND data_type = ?',
                (event['source_url'], 'sportsbook')
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing event
                event_id = existing[0]
                cursor.execute('''
                    UPDATE scraped_events
                    SET sport = ?, competition = ?, event_name = ?, start_time = ?,
                        is_live = ?, status = ?, scraped_at = ?, data_source = ?, data_type = ?
                    WHERE id = ?
                ''', (
                    event['sport'],
                    event.get('competition', ''),
                    event['event_name'],
                    event.get('start_time'),
                    event.get('is_live', 0),
                    event.get('status', 'upcoming'),
                    event['scraped_at'],
                    'real_scrape',
                    'sportsbook',
                    event_id
                ))

                # Delete old odds and insert new ones
                cursor.execute('DELETE FROM scraped_odds WHERE event_id = ?', (event_id,))
            else:
                # Insert new event
                cursor.execute('''
                    INSERT INTO scraped_events
                    (sport, competition, event_name, start_time, is_live, status,
                     scraped_at, source_url, data_source, data_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event['sport'],
                    event.get('competition', ''),
                    event['event_name'],
                    event.get('start_time'),
                    event.get('is_live', 0),
                    event.get('status', 'upcoming'),
                    event['scraped_at'],
                    event['source_url'],
                    'real_scrape',
                    'sportsbook'
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
