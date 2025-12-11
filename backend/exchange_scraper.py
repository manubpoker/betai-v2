"""
BetAI v2 - Exchange Scraper Module

Scrapes REAL exchange betting data from Betfair Exchange using Playwright.
Exchange URLs: betfair.com/exchange/plus/en/{sport}-betting-1/{page}

Features:
- Scrapes ALL pages of events (pagination support)
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

# Sport configurations with base URLs and expected page counts
SPORT_CONFIG = {
    "football": {
        "base_url": "https://www.betfair.com/exchange/plus/en/football-betting-1",
        "max_pages": 30,  # Will auto-detect actual count
    },
    "tennis": {
        "base_url": "https://www.betfair.com/exchange/plus/en/tennis-betting-2",
        "max_pages": 10,
    },
    "basketball": {
        "base_url": "https://www.betfair.com/exchange/plus/en/basketball-betting-10",
        "max_pages": 5,
    },
    "horse-racing": {
        "base_url": "https://www.betfair.com/exchange/plus/en/horse-racing-betting-7",
        "max_pages": 10,
    },
    "cricket": {
        "base_url": "https://www.betfair.com/exchange/plus/en/cricket-betting-4",
        "max_pages": 5,
    },
    "golf": {
        "base_url": "https://www.betfair.com/exchange/plus/en/golf-betting-3",
        "max_pages": 3,
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


def get_max_page_number(page: Page) -> int:
    """Extract the maximum page number from pagination."""
    try:
        max_page = page.evaluate("""
            () => {
                // Look for pagination links
                const pageLinks = document.querySelectorAll('a[href*="betting-"][href$="/"]');
                let maxPage = 1;

                pageLinks.forEach(link => {
                    const href = link.getAttribute('href') || '';
                    const match = href.match(/\\/(\\d+)\\/?$/);
                    if (match) {
                        const pageNum = parseInt(match[1]);
                        if (pageNum > maxPage) maxPage = pageNum;
                    }
                });

                // Also check pagination container
                const pagination = document.querySelector('.pagination, [class*="pagination"]');
                if (pagination) {
                    const links = pagination.querySelectorAll('a');
                    links.forEach(link => {
                        const text = link.textContent.trim();
                        const num = parseInt(text);
                        if (!isNaN(num) && num > maxPage) maxPage = num;
                    });
                }

                return maxPage;
            }
        """)
        return max_page if max_page > 0 else 1
    except:
        return 1


def scrape_exchange_page(page: Page, sport: str, url: str, page_num: int, order_offset: int = 0) -> List[Dict[str, Any]]:
    """Scrape a single page of exchange events."""
    events = []
    timestamp = datetime.utcnow().isoformat() + 'Z'

    try:
        print(f"    Scraping page {page_num}: {url}...", flush=True)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
        except Exception as e:
            print(f"      Navigation error: {e}", flush=True)
            return events

        time.sleep(3)  # Wait for JS rendering

        # Dismiss dialogs on first page
        if page_num == 1:
            dismiss_dialogs(page)

        # Scroll to load dynamic content
        for _ in range(3):
            page.keyboard.press("End")
            time.sleep(0.8)

        # Extract events with competition info
        raw_events = page.evaluate("""
            () => {
                const events = [];
                const seen = new Set();

                // Find all coupon cards (competition sections)
                const cards = document.querySelectorAll('.coupon-card, [class*="event-card"], [class*="market-card"]');

                cards.forEach(card => {
                    // Get competition name from card header
                    let competition = '';
                    const header = card.querySelector('.header, .coupon-header, h2, h3, [class*="header"]');
                    if (header) {
                        // Get the competition link or text
                        const compLink = header.querySelector('a');
                        if (compLink) {
                            competition = compLink.textContent.trim();
                        } else {
                            competition = header.textContent.trim();
                        }
                        // Clean up competition name
                        competition = competition.split('Multiples')[0].trim();
                        competition = competition.replace(/^\\s*>\\s*/, '').trim();
                    }

                    // Find all event rows in this card
                    const rows = card.querySelectorAll('tr, .event-row, [class*="event-line"]');

                    rows.forEach(row => {
                        // Skip header rows
                        if (row.querySelector('th')) return;

                        // Get event link and name
                        const eventLink = row.querySelector('a[href*="/market/"]');
                        if (!eventLink) return;

                        const eventUrl = eventLink.getAttribute('href') || '';
                        const eventText = eventLink.textContent.trim();

                        // Skip if already seen
                        if (seen.has(eventUrl)) return;
                        seen.add(eventUrl);

                        // Parse team names
                        let teamNames = [];
                        let timeStatus = null;  // "Starting In 7'mi", "17:30", etc.

                        // Try to find team names in spans
                        const teamSpans = eventLink.querySelectorAll('span, p');
                        teamSpans.forEach(span => {
                            const text = span.textContent.trim();
                            if (text && text.length > 1 && text.length < 50 && !text.match(/^\\d/)) {
                                teamNames.push(text);
                            }
                        });

                        // If no spans, parse from text
                        if (teamNames.length < 2 && eventText) {
                            // Extract time/status prefix first (e.g., "Starting In 7'mi", "17:30", "Today 17:30")
                            const statusPatterns = [
                                /^(Starting\\s+In\\s+[\\d']+mi?)\\s*/i,
                                /^(In-Play)\\s*/i,
                                /^(Today|Tomorrow)\\s+(\\d{1,2}:\\d{2})\\s*/i,
                                /^(\\d{1,2}\\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\\s+\\d{1,2}:\\d{2})\\s*/i,
                                /^(\\d{1,2}:\\d{2})\\s*/i
                            ];

                            let cleanText = eventText;
                            for (const pattern of statusPatterns) {
                                const match = eventText.match(pattern);
                                if (match) {
                                    timeStatus = match[0].trim();
                                    cleanText = eventText.substring(match[0].length).trim();
                                    break;
                                }
                            }

                            const parts = cleanText.split(/\\s+v\\s+/i);
                            if (parts.length >= 2) {
                                teamNames = parts.slice(0, 2).map(p => p.trim());
                            } else if (cleanText.length > 0) {
                                teamNames = [cleanText];
                            }
                        }

                        if (teamNames.length < 1) return;

                        // Build event name (clean, without time prefix)
                        const eventName = teamNames.length >= 2
                            ? teamNames[0] + ' v ' + teamNames[1]
                            : teamNames[0];

                        // Get start time from timeStatus or extracted time
                        let startTime = null;
                        if (timeStatus) {
                            startTime = timeStatus;
                        } else {
                            const timeMatch = eventText.match(/(\\d{1,2}:\\d{2})/);
                            if (timeMatch) startTime = timeMatch[1];
                        }

                        // Check if live
                        const isLive = row.querySelector('.inplay-icon, [class*="inplay"], [class*="live"]') !== null ||
                                      eventText.toLowerCase().includes('in-play');

                        // Get back odds
                        const backButtons = row.querySelectorAll('.back button, button.back, [class*="back"] button');
                        const backOdds = [];
                        backButtons.forEach(btn => {
                            const label = btn.querySelector('label, span');
                            if (label) {
                                const price = parseFloat(label.textContent.trim());
                                if (!isNaN(price) && price > 1) {
                                    backOdds.push(price);
                                }
                            }
                        });

                        // Get lay odds
                        const layButtons = row.querySelectorAll('.lay button, button.lay, [class*="lay"] button');
                        const layOdds = [];
                        layButtons.forEach(btn => {
                            const label = btn.querySelector('label, span');
                            if (label) {
                                const price = parseFloat(label.textContent.trim());
                                if (!isNaN(price) && price > 1) {
                                    layOdds.push(price);
                                }
                            }
                        });

                        events.push({
                            eventName,
                            teamNames,
                            competition: competition || 'Other',
                            eventUrl,
                            startTime,
                            isLive,
                            backOdds: backOdds.slice(0, 3),
                            layOdds: layOdds.slice(0, 3),
                            scrapeOrder: events.length  // Preserve order within page
                        });
                    });
                });

                // Fallback: If no cards found, try generic approach
                if (events.length === 0) {
                    // Look for any event links
                    const allEventLinks = document.querySelectorAll('a[href*="/market/"]');

                    allEventLinks.forEach(link => {
                        const url = link.getAttribute('href') || '';
                        if (seen.has(url)) return;
                        seen.add(url);

                        const text = link.textContent.trim();
                        if (!text || text.length < 5) return;

                        // Try to find parent row for odds
                        let row = link.closest('tr, div');
                        for (let i = 0; i < 5 && row; i++) {
                            const backs = row.querySelectorAll('.back button, [class*="back"] button');
                            if (backs.length > 0) break;
                            row = row.parentElement;
                        }

                        // Parse event name
                        let cleanText = text.replace(/^(Today|Tomorrow|\\d{1,2}:\\d{2}|\\d{1,2}\\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec))\\s*/gi, '');
                        cleanText = cleanText.replace(/\\d+\\s*Unmatched.*$/i, '').trim();

                        const parts = cleanText.split(/\\s+v\\s+/i);
                        const teamNames = parts.length >= 2 ? parts.slice(0, 2) : [cleanText];
                        const eventName = teamNames.join(' v ');

                        // Get odds from row
                        const backOdds = [];
                        const layOdds = [];

                        if (row) {
                            row.querySelectorAll('.back button label, [class*="back"] button label').forEach(l => {
                                const p = parseFloat(l.textContent);
                                if (!isNaN(p) && p > 1) backOdds.push(p);
                            });
                            row.querySelectorAll('.lay button label, [class*="lay"] button label').forEach(l => {
                                const p = parseFloat(l.textContent);
                                if (!isNaN(p) && p > 1) layOdds.push(p);
                            });
                        }

                        // Try to get competition from URL path
                        let competition = 'Other';
                        const urlMatch = url.match(/\\/([^/]+)\\/market\\//);
                        if (urlMatch) {
                            competition = urlMatch[1].replace(/-/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase());
                        }

                        events.push({
                            eventName,
                            teamNames,
                            competition,
                            eventUrl: url,
                            startTime: null,
                            isLive: false,
                            backOdds: backOdds.slice(0, 3),
                            layOdds: layOdds.slice(0, 3),
                            scrapeOrder: events.length
                        });
                    });
                }

                return events;
            }
        """)

        # Process events
        for raw in raw_events:
            event_name = normalize_name(raw.get('eventName', ''))
            if not event_name or len(event_name) < 3:
                continue

            competition = raw.get('competition', 'Other')
            if not competition or competition == '':
                competition = 'Other'

            source_url = f"https://www.betfair.com{raw.get('eventUrl', '')}" if raw.get('eventUrl') else url

            # Calculate global scrape order: page offset + position within page
            scrape_order = order_offset + raw.get('scrapeOrder', len(events))

            event = {
                "event_name": event_name,
                "sport": sport,
                "competition": competition,
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

        print(f"      Found {len(events)} events on page {page_num}", flush=True)

    except Exception as e:
        print(f"      Error scraping page {page_num}: {e}", flush=True)
        import traceback
        traceback.print_exc()

    return events


def scrape_sport_all_pages(page: Page, sport: str, config: Dict) -> List[Dict[str, Any]]:
    """Scrape all pages for a sport."""
    all_events = []
    seen_urls = set()

    base_url = config["base_url"]
    max_pages = config.get("max_pages", 10)

    print(f"  Scraping {sport} (up to {max_pages} pages)...", flush=True)

    # Scrape first page to detect actual max pages
    page.goto(base_url, wait_until="domcontentloaded", timeout=20000)
    time.sleep(3)

    actual_max = get_max_page_number(page)
    max_pages = min(max_pages, max(actual_max, 1))
    print(f"    Detected {actual_max} pages, will scrape up to {max_pages}", flush=True)

    # Scrape page 1 (already loaded)
    events = scrape_exchange_page(page, sport, base_url, 1, order_offset=0)
    for ev in events:
        if ev["source_url"] not in seen_urls:
            seen_urls.add(ev["source_url"])
            all_events.append(ev)

    # Scrape remaining pages
    for page_num in range(2, max_pages + 1):
        page_url = f"{base_url}/{page_num}"
        # Pass order_offset to maintain global ordering across pages
        events = scrape_exchange_page(page, sport, page_url, page_num, order_offset=len(all_events))

        new_count = 0
        for ev in events:
            if ev["source_url"] not in seen_urls:
                seen_urls.add(ev["source_url"])
                all_events.append(ev)
                new_count += 1

        # If no new events found, stop pagination
        if new_count == 0 and len(events) == 0:
            print(f"    No more events found, stopping at page {page_num}", flush=True)
            break

        time.sleep(1)  # Be nice to Betfair

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
    """Run a full scrape of all sports from Betfair Exchange with pagination."""
    print(f"[{datetime.utcnow().isoformat()}] Starting Betfair Exchange scrape (with pagination)...", flush=True)

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
                    events = scrape_sport_all_pages(page, sport, config)
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
