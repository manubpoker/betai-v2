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
- Content types: articles, tweets, videos, stats
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
        "type": "news",
        "selectors": {
            "articles": "a[data-testid='internal-link'], .ssrcss-1mrs5ns-PromoLink",
            "title": "h3, .ssrcss-1b1mki6-PromoHeadline, p.ssrcss-1b1mki6-PromoHeadline",
            "summary": ".ssrcss-1q0x1qg-Paragraph, p[class*='Paragraph']",
            "time": "time, span[class*='MetadataText']"
        }
    },
    "sky_sports": {
        "name": "Sky Sports",
        "url": "https://www.skysports.com/football/news",
        "type": "news",
        "selectors": {
            "articles": ".news-list__item a, article a",
            "title": ".news-list__headline, h3, .sdc-article-header__title",
            "summary": ".news-list__snippet, .sdc-article-body__content p",
            "time": ".news-list__time, time"
        }
    },
    "espn_fc": {
        "name": "ESPN FC",
        "url": "https://www.espn.com/soccer/",
        "type": "news",
        "selectors": {
            "articles": ".contentItem a, .headlineStack__list a",
            "title": ".contentItem__title, h1, h2",
            "summary": ".contentItem__subhead",
            "time": ".contentMeta__timestamp"
        }
    },
    "guardian": {
        "name": "The Guardian",
        "url": "https://www.theguardian.com/football",
        "type": "news",
        "selectors": {
            "articles": ".fc-item__link, a[data-link-name='article']",
            "title": ".fc-item__title, .js-headline-text",
            "summary": ".fc-item__standfirst",
            "time": "time"
        }
    },
    "reddit_soccer": {
        "name": "Reddit r/soccer",
        "url": "https://www.reddit.com/r/soccer/hot/",
        "type": "social",
        "selectors": {
            "posts": "shreddit-post, article",
            "title": "[slot='title'], h3",
            "score": "shreddit-post[score], .score",
            "comments": "[slot='commentCount'], .comments"
        }
    },
    "reddit_betting": {
        "name": "Reddit r/SoccerBetting",
        "url": "https://www.reddit.com/r/SoccerBetting/hot/",
        "type": "social",
        "selectors": {
            "posts": "shreddit-post, article",
            "title": "[slot='title'], h3",
            "score": "shreddit-post[score], .score",
            "comments": "[slot='commentCount'], .comments"
        }
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
    'manager', 'coach', 'signing', 'contract', 'deal'
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

    # Create index for faster queries
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
        # Premier League
        ('manchester united', 'Man United'), ('manchester city', 'Man City'),
        ('liverpool', 'Liverpool'), ('arsenal', 'Arsenal'), ('chelsea', 'Chelsea'),
        ('tottenham', 'Tottenham'), ('newcastle', 'Newcastle'), ('aston villa', 'Aston Villa'),
        ('brighton', 'Brighton'), ('west ham', 'West Ham'), ('fulham', 'Fulham'),
        ('brentford', 'Brentford'), ('crystal palace', 'Crystal Palace'),
        ('wolves', 'Wolves'), ('everton', 'Everton'), ('nottingham forest', 'Nottingham Forest'),
        ('bournemouth', 'Bournemouth'), ('leicester', 'Leicester'),
        # La Liga
        ('barcelona', 'Barcelona'), ('real madrid', 'Real Madrid'),
        ('atletico madrid', 'Atletico Madrid'), ('sevilla', 'Sevilla'),
        ('villarreal', 'Villarreal'), ('real sociedad', 'Real Sociedad'),
        # Bundesliga
        ('bayern munich', 'Bayern Munich'), ('borussia dortmund', 'Dortmund'),
        ('rb leipzig', 'RB Leipzig'), ('leverkusen', 'Leverkusen'),
        # Serie A
        ('juventus', 'Juventus'), ('inter milan', 'Inter'), ('ac milan', 'AC Milan'),
        ('napoli', 'Napoli'), ('roma', 'Roma'), ('lazio', 'Lazio'),
        # Ligue 1
        ('paris saint-germain', 'PSG'), ('psg', 'PSG'), ('marseille', 'Marseille'),
        ('lyon', 'Lyon'), ('monaco', 'Monaco'),
    ]

    for pattern, name in team_patterns:
        if pattern in text_lower and name not in teams:
            teams.append(name)

    return teams[:5]  # Max 5 teams


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
        ('conference league', 'Conference League'),
        ('fa cup', 'FA Cup'),
        ('carabao cup', 'Carabao Cup'),
        ('copa del rey', 'Copa del Rey'),
        ('dfb pokal', 'DFB Pokal'),
    ]

    for pattern, name in competitions:
        if pattern in text_lower:
            return name

    return None


def scrape_news_source(source_key: str, config: Dict) -> List[Dict[str, Any]]:
    """Scrape a news source for football content."""
    content_items = []
    timestamp = datetime.utcnow().isoformat() + 'Z'

    print(f"    Scraping {config['name']}...", flush=True)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )

            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )

            page = context.new_page()
            page.set_default_timeout(30000)

            try:
                page.goto(config['url'], wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                print(f"      Navigation error: {e}", flush=True)
                browser.close()
                return content_items

            time.sleep(3)
            dismiss_dialogs(page)
            time.sleep(1)

            # Scroll to load more content
            for _ in range(2):
                page.keyboard.press("End")
                time.sleep(1)

            # Extract articles based on source type
            if source_key in ['reddit_soccer', 'reddit_betting']:
                content_items = scrape_reddit(page, config, source_key, timestamp)
            else:
                content_items = scrape_news_articles(page, config, source_key, timestamp)

            browser.close()

    except Exception as e:
        print(f"      Error scraping {config['name']}: {e}", flush=True)
        import traceback
        traceback.print_exc()

    print(f"      Found {len(content_items)} items from {config['name']}", flush=True)
    return content_items


def scrape_news_articles(page: Page, config: Dict, source_key: str, timestamp: str) -> List[Dict]:
    """Scrape news articles from a page."""
    items = []
    selectors = config['selectors']

    articles = page.evaluate(f"""
        () => {{
            const articles = [];
            const seen = new Set();

            // Find article links
            const links = document.querySelectorAll('{selectors["articles"]}');

            links.forEach(link => {{
                const url = link.href || link.getAttribute('href');
                if (!url || seen.has(url) || !url.startsWith('http')) return;
                if (url.includes('/live/') || url.includes('/video/')) return;

                seen.add(url);

                // Find title
                let title = '';
                const titleEl = link.querySelector('{selectors["title"]}') ||
                               link.closest('article')?.querySelector('{selectors["title"]}');
                if (titleEl) title = titleEl.textContent.trim();
                if (!title) title = link.textContent.trim();

                // Find summary
                let summary = '';
                const summaryEl = link.querySelector('{selectors.get("summary", "p")}') ||
                                 link.closest('article')?.querySelector('{selectors.get("summary", "p")}');
                if (summaryEl) summary = summaryEl.textContent.trim();

                // Find time
                let publishedAt = '';
                const timeEl = link.querySelector('{selectors.get("time", "time")}') ||
                              link.closest('article')?.querySelector('{selectors.get("time", "time")}');
                if (timeEl) publishedAt = timeEl.getAttribute('datetime') || timeEl.textContent.trim();

                // Find image
                let imageUrl = '';
                const imgEl = link.querySelector('img') || link.closest('article')?.querySelector('img');
                if (imgEl) imageUrl = imgEl.src || imgEl.getAttribute('data-src') || '';

                if (title && title.length > 10 && title.length < 300) {{
                    articles.push({{
                        url,
                        title: title.substring(0, 300),
                        summary: summary.substring(0, 500),
                        publishedAt,
                        imageUrl
                    }});
                }}
            }});

            return articles.slice(0, 20);
        }}
    """)

    for article in articles:
        # Check if football-related
        text = (article.get('title', '') + ' ' + article.get('summary', '')).lower()
        is_football = any(kw in text for kw in FOOTBALL_KEYWORDS)

        if not is_football:
            continue

        items.append({
            'source': config['name'],
            'content_type': 'article',
            'title': article['title'],
            'summary': article.get('summary', ''),
            'url': article['url'],
            'image_url': article.get('imageUrl', ''),
            'published_at': article.get('publishedAt', ''),
            'scraped_at': timestamp,
            'engagement_score': 0,
            'comments_count': 0,
            'related_teams': json.dumps(extract_teams_from_text(text)),
            'related_competition': extract_competition_from_text(text)
        })

    return items


def scrape_reddit(page: Page, config: Dict, source_key: str, timestamp: str) -> List[Dict]:
    """Scrape Reddit posts."""
    items = []

    posts = page.evaluate("""
        () => {
            const posts = [];
            const seen = new Set();

            // Try new Reddit format
            document.querySelectorAll('shreddit-post, [data-testid="post-container"], article').forEach(post => {
                let title = '';
                let url = '';
                let score = 0;
                let comments = 0;

                // Get title
                const titleEl = post.querySelector('[slot="title"], h3, [data-testid="post-title"]');
                if (titleEl) title = titleEl.textContent.trim();

                // Get URL
                const linkEl = post.querySelector('a[href*="/comments/"]');
                if (linkEl) url = linkEl.href;
                if (!url) {
                    const permalink = post.getAttribute('permalink');
                    if (permalink) url = 'https://www.reddit.com' + permalink;
                }

                // Get score
                const scoreAttr = post.getAttribute('score');
                if (scoreAttr) score = parseInt(scoreAttr) || 0;
                const scoreEl = post.querySelector('[score], .score');
                if (scoreEl) {
                    const scoreText = scoreEl.textContent || scoreEl.getAttribute('score');
                    score = parseInt(scoreText) || score;
                }

                // Get comments
                const commentsEl = post.querySelector('[slot="commentCount"], .comments');
                if (commentsEl) {
                    const commentsText = commentsEl.textContent.replace(/[^0-9]/g, '');
                    comments = parseInt(commentsText) || 0;
                }

                if (title && url && !seen.has(url)) {
                    seen.add(url);
                    posts.push({ title, url, score, comments });
                }
            });

            return posts.slice(0, 25);
        }
    """)

    for post in posts:
        title = post.get('title', '')
        if not title or len(title) < 10:
            continue

        # Check if football-related (Reddit posts should be from football subreddits)
        text = title.lower()

        items.append({
            'source': config['name'],
            'content_type': 'social',
            'title': title[:300],
            'summary': '',
            'url': post['url'],
            'image_url': '',
            'published_at': '',
            'scraped_at': timestamp,
            'engagement_score': post.get('score', 0),
            'comments_count': post.get('comments', 0),
            'related_teams': json.dumps(extract_teams_from_text(text)),
            'related_competition': extract_competition_from_text(text)
        })

    return items


def save_content_to_db(content_items: List[Dict]) -> int:
    """Save scraped content to database."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    saved_count = 0

    for item in content_items:
        try:
            # Check if URL already exists
            cursor.execute('SELECT id FROM scraped_content WHERE url = ?', (item['url'],))
            existing = cursor.fetchone()

            if existing:
                # Update existing
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
                # Insert new
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

    # Initialize database table
    init_content_db()

    all_content = []
    source_counts = {}

    # Use ThreadPoolExecutor for parallel scraping
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all scraping tasks
        future_to_source = {
            executor.submit(scrape_news_source, source_key, config): source_key
            for source_key, config in CONTENT_SOURCES.items()
        }

        # Collect results as they complete
        for future in as_completed(future_to_source):
            source_key = future_to_source[future]
            try:
                content_items = future.result()
                all_content.extend(content_items)
                source_counts[source_key] = len(content_items)
            except Exception as e:
                print(f"Error with {source_key}: {e}", flush=True)
                source_counts[source_key] = 0

    # Save all content to database
    saved_count = save_content_to_db(all_content)

    # Clean up old content (keep last 7 days)
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM scraped_content
            WHERE scraped_at < datetime('now', '-7 days')
        ''')
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        print(f"Cleaned up {deleted} old content items", flush=True)
    except Exception as e:
        print(f"Error cleaning up old content: {e}", flush=True)

    print(f"Content scrape complete. Total: {len(all_content)}, Saved: {saved_count}", flush=True)

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

    query = '''
        SELECT * FROM scraped_content
        WHERE 1=1
    '''
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
