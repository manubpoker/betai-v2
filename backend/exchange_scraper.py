"""
BetAI v2 - Exchange Scraper Module

Scrapes REAL exchange betting data from Betfair Exchange using Playwright.
Exchange URLs: betfair.com/exchange/plus/{sport}

Key differences from Sportsbook:
- Exchange has BACK and LAY odds
- Odds are decimal format
- Shows liquidity/volume available
- User-to-user betting marketplace

CRITICAL REQUIREMENTS:
- NO mock data generation
- NO fake/random data
- All data comes from actual Betfair Exchange pages
- Uses page.evaluate() for DOM extraction
- All records have data_source='real_scrape' and data_type='exchange'

Structure discovered:
- .coupon-card: Competition section containers
- .mod-event-line: Event rows
- .runners: Contains team names
- .back BUTTON: Back price cells (first label = price, second = liquidity)
- .lay BUTTON: Lay price cells (same structure)
- .matched-amount-value: Total matched on event
"""

import sqlite3
import time
import re
from datetime import datetime
from typing import Dict, List, Any
from playwright.sync_api import sync_playwright, Page

# Database path
import os
DATABASE = os.path.join(os.path.dirname(__file__), 'betai.db')

# Betfair Exchange URLs
EXCHANGE_URLS = {
    "football": "https://www.betfair.com/exchange/plus/football",
    "tennis": "https://www.betfair.com/exchange/plus/tennis",
    "horse-racing": "https://www.betfair.com/exchange/plus/horse-racing",
    "basketball": "https://www.betfair.com/exchange/plus/basketball",
    "golf": "https://www.betfair.com/exchange/plus/golf",
    "cricket": "https://www.betfair.com/exchange/plus/cricket",
}


def parse_decimal_odds(odds_str: str) -> float:
    """Parse decimal odds from string."""
    if not odds_str or odds_str == "-":
        return None

    odds_str = odds_str.strip()

    try:
        return float(odds_str)
    except ValueError:
        return None


def normalize_name(name: str) -> str:
    """
    Normalize event/team names for consistent display.
    """
    if not name:
        return name

    words = name.strip().split()
    normalized = []

    for word in words:
        if word.lower() in ('vs', 'v', 'vs.'):
            normalized.append('v')
        elif word.upper() in ('FC', 'AFC', 'NBA', 'NFL', 'MLB', 'NHL', 'USA', 'UK', 'II', 'III', 'IV'):
            normalized.append(word.upper())
        else:
            normalized.append(word.capitalize())

    return ' '.join(normalized)


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


def scrape_exchange_sport(page: Page, sport: str, url: str) -> List[Dict[str, Any]]:
    """
    Scrape events for a single sport from Betfair Exchange.

    Uses the correct Betfair Exchange DOM structure:
    - .coupon-card: Competition sections
    - .mod-event-line: Event rows containing teams + odds
    - .back BUTTON: Back odds (first label = price)
    - .lay BUTTON: Lay odds (first label = price)
    """
    events = []
    seen_keys = set()
    timestamp = datetime.utcnow().isoformat() + 'Z'

    try:
        print(f"  Scraping Exchange {sport} from {url}...", flush=True)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
        except Exception as nav_err:
            print(f"    Navigation error: {nav_err}", flush=True)
            return events
        time.sleep(3)

        # Debug: Check page title
        try:
            title = page.title()
            content_len = len(page.content())
            print(f"    Page title: {title}, content length: {content_len}", flush=True)
        except Exception as debug_err:
            print(f"    Debug error: {debug_err}", flush=True)

        # Dismiss cookie consent
        dismiss_cookie_consent(page)

        # Scroll to load dynamic content
        for _ in range(4):
            page.keyboard.press("End")
            time.sleep(1.5)

        # Extract exchange data using the discovered structure
        # Structure: coupon-card > coupon-table > tbody > tr (each row is an event)
        # Each row has: first td with event info, then coupon-runner divs with back/lay buttons
        raw_events = page.evaluate("""
            () => {
                const events = [];
                const seen = new Set();

                // Find all coupon cards (competition sections)
                const cards = document.querySelectorAll('.coupon-card');

                cards.forEach(card => {
                    // Get competition name from header
                    const headerEl = card.querySelector('.coupon-header h3, .coupon-header a, [class*="header"] h3');
                    let competition = headerEl ? headerEl.textContent.trim() : '';
                    // Clean up competition name (remove "Multiples" etc)
                    competition = competition.split('Multiples')[0].trim();

                    // Find coupon table rows within this card
                    const tables = card.querySelectorAll('.coupon-table');

                    tables.forEach(table => {
                        const rows = table.querySelectorAll('tbody tr');

                        rows.forEach(row => {
                            // Get the first cell which contains event info
                            const firstCell = row.querySelector('td');
                            if (!firstCell) return;

                            const cellText = firstCell.textContent.trim();
                            if (!cellText || cellText.length < 5) return;

                            // Extract team names from the cell text
                            // Pattern: "Today 15:30Team ATeam B0 Unmatched bets..." or similar
                            // Need to parse out the team names

                            // First, try to get market-id from the link for unique identification
                            const linkEl = firstCell.querySelector('a.mod-link');
                            const marketId = linkEl ? linkEl.getAttribute('data-market-id') : null;
                            const eventUrl = linkEl ? linkEl.getAttribute('href') : '';

                            // Get start time from data attribute or text
                            let startTime = null;
                            const timeMatch = cellText.match(/(Today|Tomorrow|\\w{3})\\s+(\\d{1,2}:\\d{2})/);
                            if (timeMatch) {
                                startTime = timeMatch[2];
                            }

                            // Extract team names by parsing text after time, before "Unmatched"
                            // Remove the time prefix and "Unmatched bets" suffix
                            let namesText = cellText;

                            // Remove day/time prefix patterns like "Today 15:30", "Tomorrow 18:00", "Mon 20:00"
                            namesText = namesText.replace(/^(Today|Tomorrow|Mon|Tue|Wed|Thu|Fri|Sat|Sun|\\d{1,2}\\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec))\\s*\\d{1,2}:\\d{2}\\s*/i, '');

                            // Also remove standalone time patterns at the start
                            namesText = namesText.replace(/^\\d{1,2}:\\d{2}\\s*/, '');

                            // Remove everything from "Unmatched" or numbers like "0 Unmatched"
                            namesText = namesText.split(/\\d+\\s*Unmatched/)[0].trim();
                            namesText = namesText.split(/Unmatched/)[0].trim();

                            // For football, team names are concatenated - we need to split them
                            // They appear as "Team ATeam B" - look for capital letter patterns
                            const teamNames = [];
                            if (namesText.length > 0) {
                                // Split on capital letters that start new words (not acronyms)
                                // Pattern: split where lowercase is followed by uppercase
                                const parts = namesText.split(/(?<=[a-z])(?=[A-Z])/);
                                parts.forEach(part => {
                                    const cleaned = part.trim();
                                    if (cleaned && cleaned.length > 1 && cleaned.length < 50) {
                                        teamNames.push(cleaned);
                                    }
                                });
                            }

                            if (teamNames.length < 1) return;

                            // Construct event name
                            let eventName = teamNames.length >= 2
                                ? teamNames[0] + ' v ' + teamNames[1]
                                : teamNames[0];

                            // Skip if we've seen this event (use market-id for deduplication)
                            const key = marketId || eventName.toLowerCase();
                            if (seen.has(key)) return;
                            seen.add(key);

                            // Get back odds from coupon-runner divs
                            const runners = row.querySelectorAll('.coupon-runner');
                            const backOdds = [];
                            const layOdds = [];

                            runners.forEach(runner => {
                                // Get back price
                                const backBtn = runner.querySelector('.back');
                                if (backBtn) {
                                    const label = backBtn.querySelector('label');
                                    if (label) {
                                        const price = parseFloat(label.textContent.trim());
                                        if (!isNaN(price) && price > 1) {
                                            backOdds.push(price);
                                        }
                                    }
                                }

                                // Get lay price
                                const layBtn = runner.querySelector('.lay');
                                if (layBtn) {
                                    const label = layBtn.querySelector('label');
                                    if (label) {
                                        const price = parseFloat(label.textContent.trim());
                                        if (!isNaN(price) && price > 1) {
                                            layOdds.push(price);
                                        }
                                    }
                                }
                            });

                            // Check for live indicator - ONLY mark as live if explicit class is found
                            // Default to false unless we find clear evidence
                            const liveEl = row.querySelector('.inplay-icon, .live-icon, .event-status-inplay, [class*="inplay-indicator"], .in-play');
                            let isLive = false;
                            if (liveEl !== null) {
                                isLive = true;
                            } else {
                                // Check for explicit "In-Play" text in a dedicated status element
                                const statusEl = row.querySelector('.event-status, .inplay-status, .status-text');
                                if (statusEl && statusEl.textContent.trim().toLowerCase() === 'in-play') {
                                    isLive = true;
                                }
                            }
                            // If event has a future time like "Today 15:30", it's NOT live
                            if (cellText.match(/Today\s+\d{1,2}:\d{2}|Tomorrow|Mon\s|Tue\s|Wed\s|Thu\s|Fri\s|Sat\s|Sun\s/)) {
                                isLive = false;
                            }

                            // Get matched amount from cell text (format: £xxx,xxx)
                            const matchedMatch = cellText.match(/[£$€]([\\d,]+)/);
                            const matched = matchedMatch ? matchedMatch[0] : '';

                            events.push({
                                eventName: eventName,
                                teamNames: teamNames,
                                competition: competition,
                                backOdds: backOdds.slice(0, 3),  // First 3 back prices (1, X, 2)
                                layOdds: layOdds.slice(0, 3),    // First 3 lay prices
                                matched: matched,
                                isLive: isLive,
                                eventUrl: eventUrl || '',
                                startTime: startTime,
                                marketId: marketId
                            });
                        });
                    });
                });

                return events;
            }
        """)

        # Process extracted data
        for raw in raw_events:
            event_name = normalize_name(raw.get('eventName', ''))
            if not event_name or len(event_name) < 3:
                continue

            # Create deduplication key
            event_key = f"exchange:{event_name.lower()}:{sport.lower()}"
            if event_key in seen_keys:
                continue
            seen_keys.add(event_key)

            source_url = f"https://www.betfair.com{raw.get('eventUrl', '')}" if raw.get('eventUrl') else url

            event = {
                "event_name": event_name,
                "sport": sport,
                "competition": raw.get('competition', ''),
                "start_time": raw.get('startTime'),
                "is_live": 1 if raw.get('isLive') else 0,
                "status": "live" if raw.get('isLive') else "upcoming",
                "source_url": source_url,
                "scraped_at": timestamp,
                "data_source": "real_scrape",
                "data_type": "exchange",  # CRITICAL: Mark as exchange data
                "odds": []
            }

            # Get back and lay odds arrays
            back_odds = raw.get('backOdds', [])
            lay_odds = raw.get('layOdds', [])
            team_names = raw.get('teamNames', [])

            # For 3-way markets (football), create selections for home, draw, away
            if len(back_odds) >= 3 and len(team_names) >= 2:
                # Selection 1 (Home team)
                event["odds"].append({
                    "selection_name": team_names[0],
                    "back_odds": back_odds[0] if len(back_odds) > 0 else None,
                    "lay_odds": lay_odds[0] if len(lay_odds) > 0 else None,
                    "scraped_at": timestamp
                })
                # Selection X (Draw)
                event["odds"].append({
                    "selection_name": "The Draw",
                    "back_odds": back_odds[1] if len(back_odds) > 1 else None,
                    "lay_odds": lay_odds[1] if len(lay_odds) > 1 else None,
                    "scraped_at": timestamp
                })
                # Selection 2 (Away team)
                event["odds"].append({
                    "selection_name": team_names[1] if len(team_names) > 1 else "Away",
                    "back_odds": back_odds[2] if len(back_odds) > 2 else None,
                    "lay_odds": lay_odds[2] if len(lay_odds) > 2 else None,
                    "scraped_at": timestamp
                })
            elif len(back_odds) >= 2 and len(team_names) >= 2:
                # 2-way market (tennis, etc)
                event["odds"].append({
                    "selection_name": team_names[0],
                    "back_odds": back_odds[0] if len(back_odds) > 0 else None,
                    "lay_odds": lay_odds[0] if len(lay_odds) > 0 else None,
                    "scraped_at": timestamp
                })
                event["odds"].append({
                    "selection_name": team_names[1] if len(team_names) > 1 else "Player 2",
                    "back_odds": back_odds[1] if len(back_odds) > 1 else None,
                    "lay_odds": lay_odds[1] if len(lay_odds) > 1 else None,
                    "scraped_at": timestamp
                })
            elif len(back_odds) >= 1:
                # Single selection with best back/lay
                event["odds"].append({
                    "selection_name": team_names[0] if team_names else event_name,
                    "back_odds": back_odds[0] if back_odds else None,
                    "lay_odds": lay_odds[0] if lay_odds else None,
                    "scraped_at": timestamp
                })

            events.append(event)

        print(f"    Found {len(events)} exchange events for {sport}")

    except Exception as e:
        print(f"    Error scraping Exchange {sport}: {e}")
        import traceback
        traceback.print_exc()

    return events


def save_exchange_events_to_db(events: List[Dict[str, Any]]) -> int:
    """
    Save scraped exchange events to database.

    All events MUST have:
    - data_source='real_scrape'
    - data_type='exchange'
    """
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    saved_count = 0

    for event in events:
        # Verify data_type is exchange
        if event.get('data_type') != 'exchange':
            print(f"WARNING: Skipping non-exchange event: {event.get('event_name')}")
            continue

        try:
            # Check if event already exists by source_url and data_type
            cursor.execute(
                'SELECT id FROM scraped_events WHERE source_url = ? AND data_type = ?',
                (event['source_url'], 'exchange')
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
                    'exchange',
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
                    'exchange'
                ))
                event_id = cursor.lastrowid

            # Insert odds with BOTH back AND lay
            for odd in event.get('odds', []):
                cursor.execute('''
                    INSERT INTO scraped_odds
                    (event_id, selection_name, back_odds, lay_odds, scraped_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    event_id,
                    odd.get('selection_name', 'Unknown'),
                    odd.get('back_odds'),
                    odd.get('lay_odds'),
                    odd.get('scraped_at', event['scraped_at'])
                ))

            saved_count += 1

        except Exception as e:
            print(f"Error saving exchange event {event.get('event_name')}: {e}")

    conn.commit()
    conn.close()

    return saved_count


def run_exchange_scrape() -> Dict[str, Any]:
    """
    Run a full scrape of all sports from Betfair Exchange.

    Returns:
        Dict with:
            - total: Total events scraped
            - counts: Events per sport
    """
    print(f"[{datetime.utcnow().isoformat()}] Starting Betfair Exchange scrape...")

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

        for sport, url in EXCHANGE_URLS.items():
            try:
                events = scrape_exchange_sport(page, sport, url)
                saved = save_exchange_events_to_db(events)
                counts[sport] = saved
                total += saved
                time.sleep(2)  # Be nice to Betfair
            except Exception as e:
                print(f"Error with Exchange {sport}: {e}")
                counts[sport] = 0

        browser.close()

    print(f"Exchange scrape complete. Total events: {total}")
    return {"total": total, "counts": counts}


if __name__ == "__main__":
    # Run exchange scrape when called directly
    result = run_exchange_scrape()
    print(f"Exchange Results: {result}")
