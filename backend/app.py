"""
BetAI v2 - Flask Backend Application
Real-time Betfair scraping with Claude AI chat
"""

import os
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler

# Create Flask app
app = Flask(__name__)
CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"])

# Configuration
DATABASE = os.path.join(os.path.dirname(__file__), 'betai.db')
SCRAPE_INTERVAL_MINUTES = 15

# Scheduler for auto-refresh
scheduler = BackgroundScheduler()


# ============================================================
# DATABASE SETUP
# ============================================================

def get_db():
    """Get database connection for current request."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error):
    """Close database connection at end of request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Initialize the database with schema."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # scraped_events table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scraped_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sport TEXT NOT NULL,
            competition TEXT,
            event_name TEXT NOT NULL,
            start_time TEXT,
            is_live INTEGER DEFAULT 0,
            status TEXT DEFAULT 'upcoming',
            scraped_at TEXT NOT NULL,
            source_url TEXT NOT NULL,
            data_source TEXT DEFAULT 'real_scrape'
        )
    ''')

    # scraped_odds table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scraped_odds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER REFERENCES scraped_events(id),
            selection_name TEXT NOT NULL,
            back_odds REAL,
            lay_odds REAL,
            back_odds_fractional TEXT,
            lay_odds_fractional TEXT,
            liquidity REAL,
            scraped_at TEXT NOT NULL
        )
    ''')

    # user_bets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_bets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER REFERENCES scraped_events(id),
            selection_name TEXT NOT NULL,
            bet_type TEXT NOT NULL,
            odds REAL NOT NULL,
            stake REAL NOT NULL,
            potential_return REAL,
            status TEXT DEFAULT 'open',
            created_at TEXT NOT NULL
        )
    ''')

    # ai_conversations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL
        )
    ''')

    # ai_messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER REFERENCES ai_conversations(id),
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            model_used TEXT,
            response_source TEXT DEFAULT 'claude_api',
            created_at TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()
    print("Database initialized successfully")


# ============================================================
# VERIFICATION ENDPOINTS (CRITICAL - Create First!)
# ============================================================

@app.route('/api/verify/scrape-source', methods=['GET'])
def verify_scrape_source():
    """
    Verify that data comes from real Betfair scraping.
    This endpoint MUST return source='real_scrape'.
    """
    db = get_db()

    # Get total event count
    total = db.execute('SELECT COUNT(*) as count FROM scraped_events').fetchone()['count']

    # Get most recent event
    sample = db.execute('''
        SELECT * FROM scraped_events
        ORDER BY scraped_at DESC
        LIMIT 1
    ''').fetchone()

    if sample:
        scraped_at = datetime.fromisoformat(sample['scraped_at'].replace('Z', '+00:00'))
        age_minutes = (datetime.now(scraped_at.tzinfo) - scraped_at).total_seconds() / 60

        return jsonify({
            "source": sample['data_source'],  # MUST be "real_scrape"
            "scrape_age_minutes": round(age_minutes, 1),
            "total_events": total,
            "sample_event": {
                "event_name": sample['event_name'],
                "sport": sample['sport'],
                "source_url": sample['source_url'],
                "scraped_at": sample['scraped_at'],
                "data_source": sample['data_source']
            }
        })

    return jsonify({
        "source": "no_data",
        "scrape_age_minutes": None,
        "total_events": 0,
        "sample_event": None,
        "message": "No events scraped yet. Trigger a scrape first."
    })


@app.route('/api/verify/ai-status', methods=['GET'])
def verify_ai_status():
    """
    Verify Claude API connection status.
    This endpoint MUST return status='connected' and a valid Claude model.
    """
    from ai.claude_client import ClaudeClient

    try:
        client = ClaudeClient()
        status = client.get_status()
        return jsonify(status)
    except ValueError as e:
        # API key not set
        return jsonify({
            "status": "error",
            "model": None,
            "api_key_present": False,
            "error": str(e)
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "model": None,
            "api_key_present": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "error": str(e)
        })


@app.route('/api/verify/data-freshness', methods=['GET'])
def verify_data_freshness():
    """
    Verify that scraped data is recent (< 30 minutes).
    """
    db = get_db()

    # Get newest and oldest events
    newest = db.execute('''
        SELECT scraped_at FROM scraped_events
        ORDER BY scraped_at DESC
        LIMIT 1
    ''').fetchone()

    oldest = db.execute('''
        SELECT scraped_at FROM scraped_events
        ORDER BY scraped_at ASC
        LIMIT 1
    ''').fetchone()

    total = db.execute('SELECT COUNT(*) as count FROM scraped_events').fetchone()['count']

    if newest and oldest:
        newest_time = datetime.fromisoformat(newest['scraped_at'].replace('Z', '+00:00'))
        oldest_time = datetime.fromisoformat(oldest['scraped_at'].replace('Z', '+00:00'))
        now = datetime.now(newest_time.tzinfo)

        newest_age = (now - newest_time).total_seconds() / 60
        oldest_age = (now - oldest_time).total_seconds() / 60

        return jsonify({
            "is_fresh": newest_age < 30,
            "newest_event_age_minutes": round(newest_age, 1),
            "oldest_event_age_minutes": round(oldest_age, 1),
            "events_total": total
        })

    return jsonify({
        "is_fresh": False,
        "newest_event_age_minutes": None,
        "oldest_event_age_minutes": None,
        "events_total": 0,
        "message": "No events in database"
    })


# ============================================================
# SCRAPING ENDPOINTS
# ============================================================

# Scraper status tracking
scraper_status = {
    "status": "idle",
    "last_scrape": None,
    "events_count": {}
}


@app.route('/api/scrape/trigger', methods=['POST'])
def trigger_scrape():
    """Manually trigger a scrape of all sports."""
    from scraper import run_full_scrape

    try:
        scraper_status["status"] = "running"
        result = run_full_scrape()
        scraper_status["status"] = "idle"
        scraper_status["last_scrape"] = datetime.utcnow().isoformat() + 'Z'
        scraper_status["events_count"] = result.get("counts", {})

        return jsonify({
            "success": True,
            "message": "Scrape completed",
            "events_scraped": result.get("total", 0),
            "by_sport": result.get("counts", {})
        })
    except Exception as e:
        scraper_status["status"] = "error"
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/scrape/status', methods=['GET'])
def get_scrape_status():
    """Get current scraper status."""
    return jsonify(scraper_status)


# ============================================================
# EVENTS ENDPOINTS
# ============================================================

@app.route('/api/events', methods=['GET'])
def get_events():
    """Get all events, optionally filtered by sport."""
    db = get_db()
    sport = request.args.get('sport')

    if sport:
        events = db.execute('''
            SELECT * FROM scraped_events
            WHERE sport = ?
            ORDER BY start_time ASC
        ''', (sport,)).fetchall()
    else:
        events = db.execute('''
            SELECT * FROM scraped_events
            ORDER BY sport, start_time ASC
        ''').fetchall()

    return jsonify([dict(e) for e in events])


@app.route('/api/events/<int:event_id>', methods=['GET'])
def get_event(event_id):
    """Get single event with odds."""
    db = get_db()

    event = db.execute(
        'SELECT * FROM scraped_events WHERE id = ?',
        (event_id,)
    ).fetchone()

    if not event:
        return jsonify({"error": "Event not found"}), 404

    odds = db.execute('''
        SELECT * FROM scraped_odds
        WHERE event_id = ?
        ORDER BY selection_name
    ''', (event_id,)).fetchall()

    result = dict(event)
    result['odds'] = [dict(o) for o in odds]

    return jsonify(result)


@app.route('/api/events/live', methods=['GET'])
def get_live_events():
    """Get only live events."""
    db = get_db()

    events = db.execute('''
        SELECT * FROM scraped_events
        WHERE is_live = 1 OR status = 'live'
        ORDER BY sport, start_time ASC
    ''').fetchall()

    return jsonify([dict(e) for e in events])


@app.route('/api/sports', methods=['GET'])
def get_sports():
    """Get list of sports with event counts."""
    db = get_db()

    sports = db.execute('''
        SELECT sport as name, COUNT(*) as count
        FROM scraped_events
        GROUP BY sport
        ORDER BY count DESC
    ''').fetchall()

    return jsonify([dict(s) for s in sports])


# ============================================================
# BETTING ENDPOINTS
# ============================================================

@app.route('/api/bets', methods=['GET', 'POST'])
def handle_bets():
    """Get bet history or place a new bet."""
    db = get_db()

    if request.method == 'POST':
        data = request.get_json()

        # Calculate potential return
        stake = float(data.get('stake', 0))
        odds = float(data.get('odds', 0))
        bet_type = data.get('bet_type', 'back')

        if bet_type == 'back':
            potential_return = stake * odds
        else:  # lay
            potential_return = stake  # Profit is the stake

        db.execute('''
            INSERT INTO user_bets
            (event_id, selection_name, bet_type, odds, stake, potential_return, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'open', ?)
        ''', (
            data.get('event_id'),
            data.get('selection_name'),
            bet_type,
            odds,
            stake,
            potential_return,
            datetime.utcnow().isoformat() + 'Z'
        ))
        db.commit()

        return jsonify({
            "success": True,
            "message": "Bet placed successfully",
            "bet_id": db.execute('SELECT last_insert_rowid()').fetchone()[0]
        })

    # GET - return bet history
    bets = db.execute('''
        SELECT b.*, e.event_name, e.sport
        FROM user_bets b
        LEFT JOIN scraped_events e ON b.event_id = e.id
        ORDER BY b.created_at DESC
    ''').fetchall()

    return jsonify([dict(b) for b in bets])


@app.route('/api/bets/open', methods=['GET'])
def get_open_bets():
    """Get only open bets."""
    db = get_db()

    bets = db.execute('''
        SELECT b.*, e.event_name, e.sport
        FROM user_bets b
        LEFT JOIN scraped_events e ON b.event_id = e.id
        WHERE b.status = 'open'
        ORDER BY b.created_at DESC
    ''').fetchall()

    return jsonify([dict(b) for b in bets])


# ============================================================
# AI CHAT ENDPOINTS
# ============================================================

@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    """
    Send message to Claude AI.
    NO FALLBACKS - returns error if API unavailable.
    """
    from ai.claude_client import ClaudeClient

    data = request.get_json()
    message = data.get('message', '')
    conversation_id = data.get('conversation_id')

    if not message:
        return jsonify({"error": "Message is required"}), 400

    db = get_db()

    # Create or get conversation
    if not conversation_id:
        db.execute(
            'INSERT INTO ai_conversations (created_at) VALUES (?)',
            (datetime.utcnow().isoformat() + 'Z',)
        )
        db.commit()
        conversation_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]

    # Get conversation history
    history = db.execute('''
        SELECT role, content FROM ai_messages
        WHERE conversation_id = ?
        ORDER BY created_at ASC
    ''', (conversation_id,)).fetchall()

    conversation_history = [{"role": h['role'], "content": h['content']} for h in history]

    # Save user message
    db.execute('''
        INSERT INTO ai_messages (conversation_id, role, content, created_at)
        VALUES (?, 'user', ?, ?)
    ''', (conversation_id, message, datetime.utcnow().isoformat() + 'Z'))
    db.commit()

    # Call Claude API - NO FALLBACK ON ERROR
    try:
        client = ClaudeClient()
        result = client.chat(message, conversation_history)

        # Save assistant message with model info
        db.execute('''
            INSERT INTO ai_messages
            (conversation_id, role, content, model_used, response_source, created_at)
            VALUES (?, 'assistant', ?, ?, ?, ?)
        ''', (
            conversation_id,
            result['response'],
            result['model'],
            result['response_source'],
            datetime.utcnow().isoformat() + 'Z'
        ))
        db.commit()

        return jsonify({
            "response": result['response'],
            "model": result['model'],
            "response_source": result['response_source'],
            "conversation_id": conversation_id
        })

    except Exception as e:
        # Return error - NO FALLBACK TO TEMPLATE/MOCK RESPONSE
        return jsonify({
            "error": str(e),
            "message": "AI service unavailable. Please check API key."
        }), 500


@app.route('/api/ai/conversations', methods=['GET'])
def get_conversations():
    """List all AI conversations."""
    db = get_db()

    conversations = db.execute('''
        SELECT c.id, c.created_at,
               (SELECT content FROM ai_messages
                WHERE conversation_id = c.id AND role = 'user'
                ORDER BY created_at ASC LIMIT 1) as first_message
        FROM ai_conversations c
        ORDER BY c.created_at DESC
    ''').fetchall()

    return jsonify([dict(c) for c in conversations])


@app.route('/api/ai/conversations/<int:conv_id>', methods=['GET'])
def get_conversation(conv_id):
    """Get full conversation history."""
    db = get_db()

    messages = db.execute('''
        SELECT * FROM ai_messages
        WHERE conversation_id = ?
        ORDER BY created_at ASC
    ''', (conv_id,)).fetchall()

    return jsonify([dict(m) for m in messages])


# ============================================================
# SCHEDULER SETUP
# ============================================================

def scheduled_scrape():
    """Run scrape on schedule."""
    from scraper import run_full_scrape

    print(f"[{datetime.utcnow().isoformat()}] Running scheduled scrape...")
    try:
        with app.app_context():
            result = run_full_scrape()
            scraper_status["last_scrape"] = datetime.utcnow().isoformat() + 'Z'
            scraper_status["events_count"] = result.get("counts", {})
            print(f"Scheduled scrape complete: {result.get('total', 0)} events")
    except Exception as e:
        print(f"Scheduled scrape error: {e}")


# ============================================================
# APP STARTUP
# ============================================================

if __name__ == '__main__':
    # Initialize database
    init_db()

    # Start scheduler for auto-refresh
    scheduler.add_job(
        scheduled_scrape,
        'interval',
        minutes=SCRAPE_INTERVAL_MINUTES,
        id='auto_scrape'
    )
    scheduler.start()
    print(f"Scheduler started: auto-refresh every {SCRAPE_INTERVAL_MINUTES} minutes")

    # Run initial scrape
    print("Running initial scrape...")
    try:
        with app.app_context():
            from scraper import run_full_scrape
            run_full_scrape()
    except Exception as e:
        print(f"Initial scrape skipped: {e}")

    # Start Flask server
    print("Starting BetAI v2 backend on port 3001...")
    app.run(host='0.0.0.0', port=3001, debug=True, use_reloader=False)
