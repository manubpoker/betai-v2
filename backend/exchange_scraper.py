"""
BetAI v2 - Exchange Scraper Module

Scrapes REAL exchange betting data from Betfair Exchange using Playwright.
Uses "Today's Card" and competition pages to get actual match fixtures (not outrights).

Features:
- Scrapes actual match fixtures from competition pages
- Properly extracts competition names
- Gets back/lay odds with decimal format
- Organizes events by competition

CRITICAL REQUIREMENTS:
- NO mock data generation
- NO fake/random data
- All data comes from actual Betfair Exchange pages
"""

import sqlite3
import time
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from playwright.sync_api import sync_playwright, Page

import os
DATABASE = os.path.join(os.path.dirname(__file__), 'betai.db')

# Sport configurations - using competition/coupon pages that show actual fixtures
# The main sport pages (/football-betting-1) show outrights, not matches
# Competition pages and "today's card" pages show actual fixtures
# NOTE: Reduced to key competitions to avoid rate limiting on Fly.io
SPORT_CONFIG = {
    "football": {
        # Football competitions with match fixtures - top leagues only
        "urls": [
            "https://www.betfair.com/exchange/plus/en/football/english-premier-league-betting-10932509",
            "https://www.betfair.com/exchange/plus/en/football/spanish-la-liga-betting-117",
            "https://www.betfair.com/exchange/plus/en/football/german-bundesliga-betting-59",
            "https://www.betfair.com/exchange/plus/en/football/italian-serie-a-betting-81",
            "https://www.betfair.com/exchange/plus/en/football/french-ligue-1-betting-55",
            "https://www.betfair.com/exchange/plus/en/football/uefa-champions-league-betting-228",
            "https://www.betfair.com/exchange/plus/en/football/english-championship-betting-7129730",
        ],
    },
}


def normalize_name(name: str) -> str:
    """Normalize event/team names for consistent display."""
    if not name:
        return name

    words = name.strip().split()
    normalized = []

    for word in words:
        if word.lower() in ('vs', 'v', 'vs.'):
            normalized.append('v')
        elif word.upper() in ('FC', 'AFC', 'NBA', 'NFL', 'MLB', 'NHL', 'USA', 'UK', 'II', 'III', 'IV', 'SC', 'CF', 'CD', 'AS', 'AC'):
            normalized.append(word.upper())
        else:
            normalized.append(word.capitalize())

    return ' '.join(normalized)


def dismiss_dialogs(page: Page):
    """Dismiss cookie consent and other dialogs."""
    selectors = [
        'button#onetrust-accept-btn-handler',
        'button[id*="accept"]',
        'button:has-text("Accept All")',
        'button:has-text("Accept")',
    ]

    for selector in selectors:
        try:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                btn.click(timeout=3000)
                time.sleep(0.5)
                return True
        except:
            pass

    try:
        page.keyboard.press("Escape")
    except:
        pass

    return False


def extract_competition_from_url(url: str) -> str:
    """Extract competition name from Betfair URL."""
    # URL format: .../football/english-premier-league-betting-10932509
    match = re.search(r'/([^/]+)-betting-\d+$', url)
    if match:
        comp_slug = match.group(1)
        # Convert slug to readable name
        name = comp_slug.replace('-', ' ').title()
        return name
    return "Other"


def scrape_competition_page(page: Page, sport: str, url: str, competition: str, order_offset: int = 0) -> List[Dict[str, Any]]:
    """Scrape a competition page for match fixtures."""
    events = []
    timestamp = datetime.utcnow().isoformat() + 'Z'

    try:
        print(f"    Scraping {competition}: {url}...", flush=True)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"      Navigation error: {e}", flush=True)
            return events

        # Wait longer for JS rendering on slower servers
        time.sleep(5)

        # Dismiss dialogs multiple times (they can re-appear)
        for _ in range(3):
            dismiss_dialogs(page)
            time.sleep(0.5)

        # Wait for event rows to appear
        try:
            page.wait_for_selector('.mod-event-line, a.mod-link', timeout=10000)
        except:
            print(f"      No event rows found after waiting", flush=True)

        # Scroll to load dynamic content
        for _ in range(3):
            page.keyboard.press("End")
            time.sleep(1)

        # Extract events - using correct Betfair Exchange selectors
        raw_events = page.evaluate("""
            () => {
                const events = [];
                const seen = new Set();

                // Find all event rows - these have class 'mod-event-line'
                const eventRows = document.querySelectorAll('.mod-event-line, tr:has(a.mod-link)');

                eventRows.forEach(row => {
                    // Find the event link
                    const link = row.querySelector('a.mod-link');
                    if (!link) return;

                    const url = link.getAttribute('href') || '';
                    if (!url || seen.has(url)) return;

                    // Skip if URL contains 'market/' (outright markets)
                    if (url.includes('/market/')) return;

                    // Must be a betting URL
                    if (!url.includes('-betting-')) return;

                    seen.add(url);

                    // Get team names from .runners list
                    const teamNames = [];
                    const runnerNames = row.querySelectorAll('.runners .name, ul.runners li.name');
                    runnerNames.forEach(el => {
                        const name = el.textContent.trim();
                        if (name && name.length > 0 && name.length < 50) {
                            teamNames.push(name);
                        }
                    });

                    // Fallback: parse from URL
                    if (teamNames.length < 2) {
                        const urlMatch = url.match(/\\/([^/]+)-v-([^/]+)-betting/i);
                        if (urlMatch) {
                            teamNames.push(urlMatch[1].replace(/-/g, ' '));
                            teamNames.push(urlMatch[2].replace(/-/g, ' '));
                        }
                    }

                    if (teamNames.length < 2) return;

                    const eventName = teamNames[0] + ' v ' + teamNames[1];

                    // Get start time from the link text (format: "Dec 13 15:00...")
                    let startTime = null;
                    const linkText = link.textContent.trim();
                    const timeMatch = linkText.match(/([A-Z][a-z]{2}\\s+\\d{1,2}\\s+\\d{1,2}:\\d{2})/i);
                    if (timeMatch) {
                        startTime = timeMatch[1];
                    } else {
                        const simpleTime = linkText.match(/(\\d{1,2}:\\d{2})/);
                        if (simpleTime) startTime = simpleTime[1];
                    }

                    // Get odds - look for back/lay buttons in coupon-runners
                    const backOdds = [];
                    const layOdds = [];

                    // Back odds - first button in each runner
                    const couponRunners = row.querySelectorAll('.coupon-runner');
                    couponRunners.forEach((runner, idx) => {
                        const buttons = runner.querySelectorAll('button');
                        if (buttons.length >= 1) {
                            // First button is back
                            const backPrice = parseFloat(buttons[0].textContent.trim());
                            if (!isNaN(backPrice) && backPrice > 1 && backPrice < 1000) {
                                backOdds.push(backPrice);
                            }
                        }
                        if (buttons.length >= 2) {
                            // Second button is lay
                            const layPrice = parseFloat(buttons[1].textContent.trim());
                            if (!isNaN(layPrice) && layPrice > 1 && layPrice < 1000) {
                                layOdds.push(layPrice);
                            }
                        }
                    });

                    // Fallback: try other selector patterns
                    if (backOdds.length === 0) {
                        row.querySelectorAll('.back button, [class*="back"] button').forEach(btn => {
                            const price = parseFloat(btn.textContent.trim());
                            if (!isNaN(price) && price > 1 && price < 1000) {
                                backOdds.push(price);
                            }
                        });
                    }

                    if (layOdds.length === 0) {
                        row.querySelectorAll('.lay button, [class*="lay"] button').forEach(btn => {
                            const price = parseFloat(btn.textContent.trim());
                            if (!isNaN(price) && price > 1 && price < 1000) {
                                layOdds.push(price);
                            }
                        });
                    }

                    // Check if live - be more specific to avoid false positives
                    // Look for specific in-play indicators: "inplay-indicator", "icon-inplay", actual "In-Play" text
                    const inplayIndicator = row.querySelector('.inplay-indicator, .icon-inplay, [data-inplay="true"]');
                    const hasInPlayText = linkText.toLowerCase().includes('in-play') ||
                                         linkText.toLowerCase().includes('in play') ||
                                         row.textContent.toLowerCase().includes('in-play');
                    // Also check for specific time indicators that mean NOT live
                    const hasTimeIndicator = /\\d{1,2}:\\d{2}/.test(linkText) && !hasInPlayText;
                    const isLive = (inplayIndicator !== null || hasInPlayText) && !hasTimeIndicator;

                    events.push({
                        eventName,
                        teamNames: teamNames.slice(0, 2),
                        competition: '',
                        eventUrl: url,
                        startTime,
                        isLive: !!isLive,
                        backOdds: backOdds.slice(0, 3),
                        layOdds: layOdds.slice(0, 3),
                        scrapeOrder: events.length
                    });
                });

                return events;
            }
        """)

        # Process events
        for raw in raw_events:
            event_name = normalize_name(raw.get('eventName', ''))
            if not event_name or len(event_name) < 3:
                continue

            # Use the competition passed in (from URL), fall back to scraped or default
            event_competition = competition
            if not event_competition or event_competition == 'Other':
                event_competition = raw.get('competition', 'Other')
            if not event_competition or event_competition == '':
                event_competition = 'Other'

            source_url = f"https://www.betfair.com{raw.get('eventUrl', '')}" if raw.get('eventUrl') else url

            # Calculate global scrape order: offset + position within page
            scrape_order = order_offset + raw.get('scrapeOrder', len(events))

            event = {
                "event_name": event_name,
                "sport": sport,
                "competition": event_competition,
                "start_time": raw.get('startTime'),
                "is_live": 1 if raw.get('isLive') else 0,
                "status": "live" if raw.get('isLive') else "upcoming",
                "source_url": source_url,
                "scraped_at": timestamp,
                "data_source": "real_scrape",
                "data_type": "exchange",
                "scrape_order": scrape_order,
                "odds": []
            }

            # Process odds
            back_odds = raw.get('backOdds', [])
            lay_odds = raw.get('layOdds', [])
            team_names = raw.get('teamNames', [])

            # Determine number of selections based on odds count
            num_selections = max(len(back_odds), len(lay_odds), 2)
            if num_selections == 3:  # 3-way market (football)
                selections = [
                    team_names[0] if len(team_names) > 0 else "Home",
                    "The Draw",
                    team_names[1] if len(team_names) > 1 else "Away"
                ]
            else:  # 2-way market
                selections = [
                    team_names[0] if len(team_names) > 0 else "Selection 1",
                    team_names[1] if len(team_names) > 1 else "Selection 2"
                ]

            for i, sel_name in enumerate(selections):
                event["odds"].append({
                    "selection_name": normalize_name(sel_name),
                    "back_odds": back_odds[i] if i < len(back_odds) else None,
                    "lay_odds": lay_odds[i] if i < len(lay_odds) else None,
                    "scraped_at": timestamp
                })

            events.append(event)

        print(f"      Found {len(events)} events in {competition}", flush=True)

    except Exception as e:
        print(f"      Error scraping {competition}: {e}", flush=True)
        import traceback
        traceback.print_exc()

    return events


def scrape_sport_competitions(page: Page, sport: str, config: Dict) -> List[Dict[str, Any]]:
    """Scrape all competition pages for a sport."""
    all_events = []
    seen_urls = set()

    urls = config.get("urls", [])
    print(f"  Scraping {sport} ({len(urls)} competitions)...", flush=True)

    for url in urls:
        # Extract competition name from URL
        competition = extract_competition_from_url(url)

        # Scrape this competition page
        events = scrape_competition_page(page, sport, url, competition, order_offset=len(all_events))

        # Add unique events
        for ev in events:
            if ev["source_url"] not in seen_urls:
                seen_urls.add(ev["source_url"])
                all_events.append(ev)

        time.sleep(3)  # Be nice to Betfair - avoid rate limiting

    print(f"  Total {sport} events: {len(all_events)}", flush=True)
    return all_events


def save_exchange_events_to_db(events: List[Dict[str, Any]]) -> int:
    """Save scraped exchange events to database."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    saved_count = 0

    for event in events:
        if event.get('data_type') != 'exchange':
            continue

        try:
            # Check if event exists
            cursor.execute(
                'SELECT id FROM scraped_events WHERE source_url = ? AND data_type = ?',
                (event['source_url'], 'exchange')
            )
            existing = cursor.fetchone()

            if existing:
                event_id = existing[0]
                cursor.execute('''
                    UPDATE scraped_events
                    SET sport = ?, competition = ?, event_name = ?, start_time = ?,
                        is_live = ?, status = ?, scraped_at = ?, data_source = ?, data_type = ?, scrape_order = ?
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
                    event.get('scrape_order', 0),
                    event_id
                ))
                cursor.execute('DELETE FROM scraped_odds WHERE event_id = ?', (event_id,))
            else:
                cursor.execute('''
                    INSERT INTO scraped_events
                    (sport, competition, event_name, start_time, is_live, status,
                     scraped_at, source_url, data_source, data_type, scrape_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    'exchange',
                    event.get('scrape_order', 0)
                ))
                event_id = cursor.lastrowid

            # Insert odds
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
            print(f"Error saving event {event.get('event_name')}: {e}", flush=True)

    conn.commit()
    conn.close()
    return saved_count


def run_exchange_scrape() -> Dict[str, Any]:
    """Run a full scrape of all sports from Betfair Exchange competition pages."""
    print(f"[{datetime.utcnow().isoformat()}] Starting Betfair Exchange scrape (competition pages)...", flush=True)

    counts = {}
    total = 0

    print("Launching Exchange Playwright browser...", flush=True)
    try:
        with sync_playwright() as p:
            print("Exchange Playwright context created, launching Chromium...", flush=True)
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            print("Exchange browser launched successfully!", flush=True)

            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            print("Exchange browser context created.", flush=True)

            page = context.new_page()
            print("Exchange new page created, starting sport scrapes...", flush=True)

            for sport, config in SPORT_CONFIG.items():
                try:
                    print(f"  Starting Exchange scrape for {sport}...", flush=True)
                    events = scrape_sport_competitions(page, sport, config)
                    saved = save_exchange_events_to_db(events)
                    counts[sport] = saved
                    total += saved
                    print(f"  Completed Exchange {sport}: {saved} events saved", flush=True)
                    time.sleep(2)
                except Exception as e:
                    print(f"Error with Exchange {sport}: {e}", flush=True)
                    import traceback
                    traceback.print_exc()
                    counts[sport] = 0

            browser.close()
            print("Exchange browser closed.", flush=True)

    except Exception as e:
        print(f"CRITICAL ERROR in run_exchange_scrape: {e}", flush=True)
        import traceback
        traceback.print_exc()

    print(f"Exchange scrape complete. Total events: {total}", flush=True)
    return {"total": total, "counts": counts}


if __name__ == "__main__":
    result = run_exchange_scrape()
    print(f"Exchange Results: {result}")
