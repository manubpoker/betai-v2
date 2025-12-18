"""
BetAI v2 - Content Scraper Module

Scrapes REAL football content from multiple sources using Playwright.
Uses concurrent workers for parallel scraping.

Sources:
- BBC Sport Football
- Sky Sports Football
- ESPN FC
- The Guardian Football
- Reddit r/soccer

Features:
- Multi-threaded scraping with worker pool
- Content types: articles, social posts
- Match-aware content linking
- Rate limiting and polite scraping
"""

import sqlite3
import time
import re
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright, Page, Browser

import os
DATABASE = os.path.join(os.path.dirname(__file__), 'betai.db')

# Content source configurations
CONTENT_SOURCES = {
    "bbc_sport": {
        "name": "BBC Sport",
        "url": "https://www.bbc.com/sport/football",
        "type": "news"
    },
    "sky_sports": {
        "name": "Sky Sports",
        "url": "https://www.skysports.com/football/news",
        "type": "news"
    },
    "espn_fc": {
        "name": "ESPN FC",
        "url": "https://www.espn.com/soccer/",
        "type": "news"
    },
    "guardian": {
        "name": "The Guardian",
        "url": "https://www.theguardian.com/football",
        "type": "news"
    },
    "reddit_soccer": {
        "name": "Reddit r/soccer",
        "url": "https://old.reddit.com/r/soccer/",
        "type": "social"
    },
    "reddit_betting": {
        "name": "Reddit r/SoccerBetting",
        "url": "https://old.reddit.com/r/SoccerBetting/",
        "type": "social"
    }
}

# Football-related keywords for filtering
FOOTBALL_KEYWORDS = [
    'premier league', 'la liga', 'bundesliga', 'serie a', 'ligue 1',
    'champions league', 'europa league', 'world cup', 'euro 202',
    'manchester', 'liverpool', 'arsenal', 'chelsea', 'tottenham', 'city',
    'barcelona', 'real madrid', 'atletico', 'bayern', 'dortmund',
    'juventus', 'inter', 'milan', 'napoli', 'roma',
    'psg', 'marseille', 'lyon',
    'transfer', 'goal', 'score', 'match', 'lineup', 'injury',
    'manager', 'coach', 'signing', 'contract', 'deal',
    'football', 'soccer', 'fc', 'united', 'league'
]


def init_content_db():
    """Initialize content table in database."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scraped_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            content_type TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            url TEXT UNIQUE,
            image_url TEXT,
            author TEXT,
            published_at TEXT,
            scraped_at TEXT NOT NULL,
            engagement_score INTEGER DEFAULT 0,
            comments_count INTEGER DEFAULT 0,
            related_teams TEXT,
            related_competition TEXT
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_content_scraped_at ON scraped_content(scraped_at DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_content_type ON scraped_content(content_type)')

    conn.commit()
    conn.close()


def dismiss_dialogs(page: Page):
    """Dismiss cookie consent and other dialogs."""
    selectors = [
        'button#onetrust-accept-btn-handler',
        'button[id*="accept"]',
        'button:has-text("Accept All")',
        'button:has-text("Accept")',
        'button:has-text("I Accept")',
        'button:has-text("Got it")',
        'button:has-text("OK")',
        'button:has-text("Continue")',
        '[aria-label="Close"]',
    ]

    for selector in selectors:
        try:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                btn.click(timeout=2000)
                time.sleep(0.3)
        except:
            pass

    try:
        page.keyboard.press("Escape")
    except:
        pass


def extract_teams_from_text(text: str) -> List[str]:
    """Extract team names from text content."""
    teams = []
    text_lower = text.lower()

    team_patterns = [
        ('manchester united', 'Man United'), ('manchester city', 'Man City'),
        ('liverpool', 'Liverpool'), ('arsenal', 'Arsenal'), ('chelsea', 'Chelsea'),
        ('tottenham', 'Tottenham'), ('newcastle', 'Newcastle'), ('aston villa', 'Aston Villa'),
        ('brighton', 'Brighton'), ('west ham', 'West Ham'), ('fulham', 'Fulham'),
        ('brentford', 'Brentford'), ('crystal palace', 'Crystal Palace'),
        ('wolves', 'Wolves'), ('everton', 'Everton'), ('nottingham forest', 'Nottingham Forest'),
        ('bournemouth', 'Bournemouth'), ('leicester', 'Leicester'),
        ('barcelona', 'Barcelona'), ('real madrid', 'Real Madrid'),
        ('atletico madrid', 'Atletico Madrid'), ('sevilla', 'Sevilla'),
        ('bayern munich', 'Bayern Munich'), ('borussia dortmund', 'Dortmund'),
        ('juventus', 'Juventus'), ('inter milan', 'Inter'), ('ac milan', 'AC Milan'),
        ('napoli', 'Napoli'), ('roma', 'Roma'),
        ('paris saint-germain', 'PSG'), ('psg', 'PSG'),
    ]

    for pattern, name in team_patterns:
        if pattern in text_lower and name not in teams:
            teams.append(name)

    return teams[:5]


def extract_competition_from_text(text: str) -> Optional[str]:
    """Extract competition name from text."""
    text_lower = text.lower()

    competitions = [
        ('premier league', 'Premier League'),
        ('la liga', 'La Liga'),
        ('bundesliga', 'Bundesliga'),
        ('serie a', 'Serie A'),
        ('ligue 1', 'Ligue 1'),
        ('champions league', 'Champions League'),
        ('europa league', 'Europa League'),
        ('fa cup', 'FA Cup'),
        ('carabao cup', 'Carabao Cup'),
    ]

    for pattern, name in competitions:
        if pattern in text_lower:
            return name

    return None


def scrape_bbc_sport(page: Page, timestamp: str) -> List[Dict]:
    """Scrape BBC Sport football page."""
    items = []

    try:
        page.goto("https://www.bbc.com/sport/football", wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)
        dismiss_dialogs(page)

        # Scroll to load content
        for _ in range(2):
            page.keyboard.press("End")
            time.sleep(1)

        articles = page.evaluate("""
            () => {
                const articles = [];
                const seen = new Set();

                // Find all promo links on BBC Sport
                document.querySelectorAll('a[href*="/sport/football/"]').forEach(link => {
                    const url = link.href;
                    if (!url || seen.has(url)) return;
                    if (url.includes('/live/') || url.includes('/av/')) return;
                    if (!url.match(/\\/sport\\/football\\/\\d+/)) return;

                    seen.add(url);

                    // Get title from heading or link text
                    let title = '';
                    const heading = link.querySelector('h3, h2, span[class*="Headline"], p[class*="Headline"]');
                    if (heading) title = heading.textContent.trim();
                    if (!title) title = link.textContent.trim();

                    // Get image
                    let imageUrl = '';
                    const container = link.closest('div, article, li');
                    if (container) {
                        const img = container.querySelector('img');
                        if (img) imageUrl = img.src || img.getAttribute('data-src') || '';
                    }

                    // Clean up title
                    title = title.replace(/\\s+/g, ' ').trim();

                    if (title && title.length > 15 && title.length < 200) {
                        articles.push({ url, title, imageUrl });
                    }
                });

                return articles.slice(0, 15);
            }
        """)

        for article in articles:
            title = article.get('title', '')
            text = title.lower()

            if any(kw in text for kw in FOOTBALL_KEYWORDS):
                items.append({
                    'source': 'BBC Sport',
                    'content_type': 'article',
                    'title': title,
                    'summary': '',
                    'url': article['url'],
                    'image_url': article.get('imageUrl', ''),
                    'published_at': '',
                    'scraped_at': timestamp,
                    'engagement_score': 0,
                    'comments_count': 0,
                    'related_teams': json.dumps(extract_teams_from_text(title)),
                    'related_competition': extract_competition_from_text(title)
                })

    except Exception as e:
        print(f"      BBC Sport error: {e}", flush=True)

    return items


def scrape_sky_sports(page: Page, timestamp: str) -> List[Dict]:
    """Scrape Sky Sports football news."""
    items = []

    try:
        page.goto("https://www.skysports.com/football/news", wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)
        dismiss_dialogs(page)

        for _ in range(2):
            page.keyboard.press("End")
            time.sleep(1)

        articles = page.evaluate("""
            () => {
                const articles = [];
                const seen = new Set();

                document.querySelectorAll('.news-list__item a, a[href*="/football/news/"]').forEach(link => {
                    const url = link.href;
                    if (!url || seen.has(url)) return;
                    if (!url.includes('/football/')) return;

                    seen.add(url);

                    let title = '';
                    const headline = link.querySelector('.news-list__headline, h3, h4');
                    if (headline) title = headline.textContent.trim();
                    if (!title) title = link.textContent.trim();

                    // Get image
                    let imageUrl = '';
                    const container = link.closest('.news-list__item, article, div');
                    if (container) {
                        const img = container.querySelector('img');
                        if (img) imageUrl = img.src || img.getAttribute('data-src') || '';
                    }

                    title = title.replace(/\\s+/g, ' ').trim();

                    if (title && title.length > 15 && title.length < 200) {
                        articles.push({ url, title, imageUrl });
                    }
                });

                return articles.slice(0, 15);
            }
        """)

        for article in articles:
            title = article.get('title', '')
            text = title.lower()

            if any(kw in text for kw in FOOTBALL_KEYWORDS):
                items.append({
                    'source': 'Sky Sports',
                    'content_type': 'article',
                    'title': title,
                    'summary': '',
                    'url': article['url'],
                    'image_url': article.get('imageUrl', ''),
                    'published_at': '',
                    'scraped_at': timestamp,
                    'engagement_score': 0,
                    'comments_count': 0,
                    'related_teams': json.dumps(extract_teams_from_text(title)),
                    'related_competition': extract_competition_from_text(title)
                })

    except Exception as e:
        print(f"      Sky Sports error: {e}", flush=True)

    return items


def scrape_espn(page: Page, timestamp: str) -> List[Dict]:
    """Scrape ESPN FC."""
    items = []

    try:
        page.goto("https://www.espn.com/soccer/", wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)
        dismiss_dialogs(page)

        for _ in range(2):
            page.keyboard.press("End")
            time.sleep(1)

        articles = page.evaluate("""
            () => {
                const articles = [];
                const seen = new Set();

                document.querySelectorAll('a[href*="/soccer/story/"], a[href*="/soccer/recap/"]').forEach(link => {
                    const url = link.href;
                    if (!url || seen.has(url)) return;

                    seen.add(url);

                    let title = '';
                    const headline = link.querySelector('h1, h2, h3, .contentItem__title');
                    if (headline) title = headline.textContent.trim();
                    if (!title) title = link.textContent.trim();

                    // Get image
                    let imageUrl = '';
                    const container = link.closest('.contentItem, article, div');
                    if (container) {
                        const img = container.querySelector('img');
                        if (img) imageUrl = img.src || img.getAttribute('data-src') || '';
                    }

                    title = title.replace(/\\s+/g, ' ').trim();

                    if (title && title.length > 15 && title.length < 200) {
                        articles.push({ url, title, imageUrl });
                    }
                });

                return articles.slice(0, 15);
            }
        """)

        for article in articles:
            title = article.get('title', '')
            text = title.lower()

            if any(kw in text for kw in FOOTBALL_KEYWORDS):
                items.append({
                    'source': 'ESPN FC',
                    'content_type': 'article',
                    'title': title,
                    'summary': '',
                    'url': article['url'],
                    'image_url': article.get('imageUrl', ''),
                    'published_at': '',
                    'scraped_at': timestamp,
                    'engagement_score': 0,
                    'comments_count': 0,
                    'related_teams': json.dumps(extract_teams_from_text(title)),
                    'related_competition': extract_competition_from_text(title)
                })

    except Exception as e:
        print(f"      ESPN error: {e}", flush=True)

    return items


def scrape_guardian(page: Page, timestamp: str) -> List[Dict]:
    """Scrape The Guardian football."""
    items = []

    try:
        page.goto("https://www.theguardian.com/football", wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)
        dismiss_dialogs(page)

        for _ in range(2):
            page.keyboard.press("End")
            time.sleep(1)

        articles = page.evaluate("""
            () => {
                const articles = [];
                const seen = new Set();

                document.querySelectorAll('a[href*="/football/"][href*="/20"]').forEach(link => {
                    const url = link.href;
                    if (!url || seen.has(url)) return;
                    if (url.includes('/live/') || url.includes('/video/')) return;

                    seen.add(url);

                    let title = '';
                    const headline = link.querySelector('h3, h2, span[class*="headline"]');
                    if (headline) title = headline.textContent.trim();
                    if (!title && link.getAttribute('aria-label')) title = link.getAttribute('aria-label');
                    if (!title) title = link.textContent.trim();

                    // Get image
                    let imageUrl = '';
                    const container = link.closest('.fc-item, article, li');
                    if (container) {
                        const img = container.querySelector('img');
                        if (img) imageUrl = img.src || img.getAttribute('data-src') || '';
                    }

                    title = title.replace(/\\s+/g, ' ').trim();

                    if (title && title.length > 15 && title.length < 250) {
                        articles.push({ url, title, imageUrl });
                    }
                });

                return articles.slice(0, 15);
            }
        """)

        for article in articles:
            title = article.get('title', '')
            text = title.lower()

            if any(kw in text for kw in FOOTBALL_KEYWORDS):
                items.append({
                    'source': 'The Guardian',
                    'content_type': 'article',
                    'title': title,
                    'summary': '',
                    'url': article['url'],
                    'image_url': article.get('imageUrl', ''),
                    'published_at': '',
                    'scraped_at': timestamp,
                    'engagement_score': 0,
                    'comments_count': 0,
                    'related_teams': json.dumps(extract_teams_from_text(title)),
                    'related_competition': extract_competition_from_text(title)
                })

    except Exception as e:
        print(f"      Guardian error: {e}", flush=True)

    return items


def scrape_reddit(page: Page, subreddit: str, source_name: str, timestamp: str) -> List[Dict]:
    """Scrape Reddit using old.reddit.com for simpler HTML."""
    items = []

    try:
        url = f"https://old.reddit.com/r/{subreddit}/"
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        posts = page.evaluate("""
            () => {
                const posts = [];

                document.querySelectorAll('.thing.link').forEach(post => {
                    const titleEl = post.querySelector('a.title');
                    if (!titleEl) return;

                    const title = titleEl.textContent.trim();
                    const url = titleEl.href;

                    // Get score
                    const scoreEl = post.querySelector('.score.unvoted');
                    let score = 0;
                    if (scoreEl) {
                        const scoreText = scoreEl.getAttribute('title') || scoreEl.textContent;
                        score = parseInt(scoreText) || 0;
                    }

                    // Get comments
                    const commentsEl = post.querySelector('.comments');
                    let comments = 0;
                    if (commentsEl) {
                        const match = commentsEl.textContent.match(/\\d+/);
                        if (match) comments = parseInt(match[0]) || 0;
                    }

                    // Get thumbnail/image
                    let imageUrl = '';
                    const thumb = post.querySelector('.thumbnail img, a.thumbnail');
                    if (thumb) {
                        if (thumb.tagName === 'IMG') {
                            imageUrl = thumb.src || '';
                        } else {
                            const img = thumb.querySelector('img');
                            if (img) imageUrl = img.src || '';
                        }
                    }
                    // Also check for direct image links
                    if (!imageUrl && post.classList.contains('link')) {
                        const directLink = post.getAttribute('data-url');
                        if (directLink && (directLink.includes('.jpg') || directLink.includes('.png') || directLink.includes('i.redd.it'))) {
                            imageUrl = directLink;
                        }
                    }

                    if (title && url) {
                        posts.push({ title, url, score, comments, imageUrl });
                    }
                });

                return posts.slice(0, 20);
            }
        """)

        for post in posts:
            title = post.get('title', '')
            if not title or len(title) < 10:
                continue

            items.append({
                'source': source_name,
                'content_type': 'social',
                'title': title[:300],
                'summary': '',
                'url': post['url'],
                'image_url': post.get('imageUrl', ''),
                'published_at': '',
                'scraped_at': timestamp,
                'engagement_score': post.get('score', 0),
                'comments_count': post.get('comments', 0),
                'related_teams': json.dumps(extract_teams_from_text(title)),
                'related_competition': extract_competition_from_text(title)
            })

    except Exception as e:
        print(f"      Reddit {subreddit} error: {e}", flush=True)

    return items


def scrape_source(source_key: str, config: Dict) -> List[Dict]:
    """Scrape a single source."""
    timestamp = datetime.utcnow().isoformat() + 'Z'
    items = []

    print(f"    Scraping {config['name']}...", flush=True)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )

            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            page = context.new_page()
            page.set_default_timeout(30000)

            if source_key == 'bbc_sport':
                items = scrape_bbc_sport(page, timestamp)
            elif source_key == 'sky_sports':
                items = scrape_sky_sports(page, timestamp)
            elif source_key == 'espn_fc':
                items = scrape_espn(page, timestamp)
            elif source_key == 'guardian':
                items = scrape_guardian(page, timestamp)
            elif source_key == 'reddit_soccer':
                items = scrape_reddit(page, 'soccer', config['name'], timestamp)
            elif source_key == 'reddit_betting':
                items = scrape_reddit(page, 'SoccerBetting', config['name'], timestamp)

            browser.close()

    except Exception as e:
        print(f"      Error scraping {config['name']}: {e}", flush=True)
        import traceback
        traceback.print_exc()

    print(f"      Found {len(items)} items from {config['name']}", flush=True)
    return items


def save_content_to_db(content_items: List[Dict]) -> int:
    """Save scraped content to database."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    saved_count = 0

    for item in content_items:
        try:
            cursor.execute('SELECT id FROM scraped_content WHERE url = ?', (item['url'],))
            existing = cursor.fetchone()

            if existing:
                cursor.execute('''
                    UPDATE scraped_content
                    SET title = ?, summary = ?, scraped_at = ?, engagement_score = ?,
                        comments_count = ?, related_teams = ?, related_competition = ?
                    WHERE id = ?
                ''', (
                    item['title'],
                    item.get('summary', ''),
                    item['scraped_at'],
                    item.get('engagement_score', 0),
                    item.get('comments_count', 0),
                    item.get('related_teams', '[]'),
                    item.get('related_competition'),
                    existing[0]
                ))
            else:
                cursor.execute('''
                    INSERT INTO scraped_content
                    (source, content_type, title, summary, url, image_url,
                     published_at, scraped_at, engagement_score, comments_count,
                     related_teams, related_competition)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    item['source'],
                    item['content_type'],
                    item['title'],
                    item.get('summary', ''),
                    item['url'],
                    item.get('image_url', ''),
                    item.get('published_at', ''),
                    item['scraped_at'],
                    item.get('engagement_score', 0),
                    item.get('comments_count', 0),
                    item.get('related_teams', '[]'),
                    item.get('related_competition')
                ))
                saved_count += 1

        except Exception as e:
            print(f"Error saving content: {e}", flush=True)

    conn.commit()
    conn.close()
    return saved_count


def run_content_scrape(max_workers: int = 3) -> Dict[str, Any]:
    """Run content scrape with multiple workers."""
    print(f"[{datetime.utcnow().isoformat()}] Starting content scrape with {max_workers} workers...", flush=True)

    init_content_db()

    all_content = []
    source_counts = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_source = {
            executor.submit(scrape_source, source_key, config): source_key
            for source_key, config in CONTENT_SOURCES.items()
        }

        for future in as_completed(future_to_source):
            source_key = future_to_source[future]
            try:
                content_items = future.result()
                all_content.extend(content_items)
                source_counts[source_key] = len(content_items)
            except Exception as e:
                print(f"Error with {source_key}: {e}", flush=True)
                source_counts[source_key] = 0

    saved_count = save_content_to_db(all_content)

    # Clean up old content
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM scraped_content WHERE scraped_at < datetime('now', '-7 days')")
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        print(f"Cleaned up {deleted} old content items", flush=True)
    except Exception as e:
        print(f"Error cleaning up: {e}", flush=True)

    print(f"Content scrape complete. Total: {len(all_content)}, Saved: {saved_count}", flush=True)
    print(f"Source breakdown: {source_counts}", flush=True)

    return {
        "total_scraped": len(all_content),
        "new_saved": saved_count,
        "source_counts": source_counts
    }


def get_content_feed(limit: int = 50, content_type: Optional[str] = None) -> List[Dict]:
    """Get content feed from database."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = 'SELECT * FROM scraped_content WHERE 1=1'
    params = []

    if content_type and content_type != 'all':
        query += ' AND content_type = ?'
        params.append(content_type)

    query += ' ORDER BY scraped_at DESC LIMIT ?'
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


if __name__ == "__main__":
    result = run_content_scrape(max_workers=3)
    print(f"Results: {result}")
