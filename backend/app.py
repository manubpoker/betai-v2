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
# CORS configuration - allow localhost for dev and production domains
CORS(app, origins=[
    "http://localhost:*",
    "http://127.0.0.1:*",
    "https://*.vercel.app",
    "https://betai-v2.vercel.app"
], supports_credentials=True)
CORS(app)  # Allow all origins in development

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
            data_source TEXT DEFAULT 'real_scrape',
            data_type TEXT DEFAULT 'sportsbook'
        )
    ''')

    # Add data_type column if it doesn't exist (migration for existing DBs)
    try:
        cursor.execute("ALTER TABLE scraped_events ADD COLUMN data_type TEXT DEFAULT 'sportsbook'")
    except:
        pass  # Column already exists

    # Add scrape_order column if it doesn't exist (for preserving Betfair page order)
    try:
        cursor.execute("ALTER TABLE scraped_events ADD COLUMN scrape_order INTEGER DEFAULT 0")
    except:
        pass  # Column already exists

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

    # Add conversation_type and event_id columns if they don't exist (migration)
    try:
        cursor.execute('ALTER TABLE ai_conversations ADD COLUMN conversation_type TEXT DEFAULT "general"')
    except:
        pass  # Column already exists
    try:
        cursor.execute('ALTER TABLE ai_conversations ADD COLUMN event_id INTEGER')
    except:
        pass  # Column already exists
    try:
        cursor.execute('ALTER TABLE ai_conversations ADD COLUMN event_name TEXT')
    except:
        pass  # Column already exists

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

    # user_balance table - tracks user's betting balance
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_balance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            balance REAL NOT NULL DEFAULT 1000.00,
            updated_at TEXT NOT NULL
        )
    ''')

    # balance_transactions table - tracks all balance changes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS balance_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            transaction_type TEXT NOT NULL,
            description TEXT,
            bet_id INTEGER REFERENCES user_bets(id),
            created_at TEXT NOT NULL
        )
    ''')

    # Add new columns to user_bets if they don't exist (for bet resolution)
    try:
        cursor.execute('ALTER TABLE user_bets ADD COLUMN result TEXT')
    except:
        pass  # Column already exists
    try:
        cursor.execute('ALTER TABLE user_bets ADD COLUMN settled_at TEXT')
    except:
        pass  # Column already exists
    try:
        cursor.execute('ALTER TABLE user_bets ADD COLUMN profit_loss REAL')
    except:
        pass  # Column already exists

    # ai_recommendations table - stores Opus 4.5 analyzed value bets
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER REFERENCES scraped_events(id),
            event_name TEXT NOT NULL,
            sport TEXT,
            competition TEXT,
            selection TEXT NOT NULL,
            opponent TEXT,
            odds REAL NOT NULL,
            stake REAL NOT NULL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')

    # Initialize balance if not exists
    cursor.execute('SELECT COUNT(*) FROM user_balance')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO user_balance (balance, updated_at) VALUES (1000.00, ?)
        ''', (datetime.utcnow().isoformat() + 'Z',))

    conn.commit()
    conn.close()
    print("Database initialized successfully")


# ============================================================
# HEALTH CHECK ENDPOINT (for Railway/deployment)
# ============================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check that returns immediately."""
    return jsonify({"status": "healthy", "service": "betai-v2"})


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
    """
    Manually trigger an exchange scrape.
    """
    from exchange_scraper import run_exchange_scrape

    try:
        scraper_status["status"] = "running"
        total = 0

        # Run exchange scraper only
        ex_result = run_exchange_scrape()
        if ex_result:
            total += ex_result.get("total", 0)

        scraper_status["status"] = "idle"
        scraper_status["last_scrape"] = datetime.utcnow().isoformat() + 'Z'
        scraper_status["events_count"] = {
            "exchange": (ex_result or {}).get("counts", {})
        }

        return jsonify({
            "success": True,
            "message": "Exchange scrape completed",
            "events_scraped": total,
            "exchange": ex_result
        })
    except Exception as e:
        scraper_status["status"] = "error"
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/scrape/status', methods=['GET'])
def get_scrape_status():
    """Get current scraper status with data freshness info."""
    db = get_db()

    # Get freshness info
    newest = db.execute('''
        SELECT scraped_at FROM scraped_events
        ORDER BY scraped_at DESC
        LIMIT 1
    ''').fetchone()

    total_events = db.execute('SELECT COUNT(*) as count FROM scraped_events').fetchone()['count']

    # Get counts by sport
    sport_counts = db.execute('''
        SELECT sport, COUNT(*) as count
        FROM scraped_events
        GROUP BY sport
    ''').fetchall()

    # Get counts by competition
    comp_counts = db.execute('''
        SELECT competition, COUNT(*) as count
        FROM scraped_events
        WHERE competition IS NOT NULL AND competition != ''
        GROUP BY competition
        ORDER BY count DESC
    ''').fetchall()

    freshness = None
    if newest:
        try:
            scraped_at = datetime.fromisoformat(newest['scraped_at'].replace('Z', '+00:00'))
            age_seconds = (datetime.now(scraped_at.tzinfo) - scraped_at).total_seconds()
            freshness = {
                "last_scrape": newest['scraped_at'],
                "age_seconds": int(age_seconds),
                "age_minutes": round(age_seconds / 60, 1),
                "is_fresh": age_seconds < 1800  # Less than 30 minutes old
            }
        except:
            pass

    return jsonify({
        **scraper_status,
        "total_events": total_events,
        "freshness": freshness,
        "sports": {s['sport']: s['count'] for s in sport_counts},
        "competitions": {c['competition']: c['count'] for c in comp_counts}
    })


# ============================================================
# EVENTS ENDPOINTS
# ============================================================

@app.route('/api/events', methods=['GET'])
def get_events():
    """Get all events with odds, optionally filtered by sport and data_type."""
    db = get_db()
    sport = request.args.get('sport')
    data_type = request.args.get('data_type')  # 'exchange' or 'sportsbook'

    # Build query based on filters
    conditions = []
    params = []

    if sport:
        conditions.append("sport = ?")
        params.append(sport)

    if data_type:
        conditions.append("data_type = ?")
        params.append(data_type)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Get events ordered by scrape_order to preserve Betfair page order
    events = db.execute(f'''
        SELECT * FROM scraped_events
        WHERE {where_clause}
        ORDER BY scrape_order ASC, id ASC
    ''', params).fetchall()

    # Get all odds in a single query for efficiency
    event_ids = [e['id'] for e in events]
    if event_ids:
        placeholders = ','.join('?' * len(event_ids))
        all_odds = db.execute(f'''
            SELECT * FROM scraped_odds
            WHERE event_id IN ({placeholders})
            ORDER BY event_id, selection_name
        ''', event_ids).fetchall()

        # Group odds by event_id
        odds_by_event = {}
        for odd in all_odds:
            eid = odd['event_id']
            if eid not in odds_by_event:
                odds_by_event[eid] = []
            odds_by_event[eid].append(dict(odd))
    else:
        odds_by_event = {}

    # Build response with odds included
    result = []
    for e in events:
        event_dict = dict(e)
        event_dict['odds'] = odds_by_event.get(e['id'], [])
        result.append(event_dict)

    return jsonify(result)


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

        if stake <= 0:
            return jsonify({"error": "Stake must be positive"}), 400

        # Calculate amount to deduct from balance
        if bet_type == 'back':
            potential_return = stake * odds
            amount_to_deduct = stake  # Back bets risk the stake
        else:  # lay
            potential_return = stake  # Profit is the stake
            amount_to_deduct = stake * (odds - 1)  # Lay bets risk the liability

        # Check balance
        current = db.execute('SELECT balance FROM user_balance ORDER BY id DESC LIMIT 1').fetchone()
        current_balance = current['balance'] if current else 1000.00

        if amount_to_deduct > current_balance:
            return jsonify({"error": "Insufficient balance", "required": amount_to_deduct, "available": current_balance}), 400

        # Deduct from balance
        new_balance = current_balance - amount_to_deduct
        db.execute('UPDATE user_balance SET balance = ?, updated_at = ?',
                   (new_balance, datetime.utcnow().isoformat() + 'Z'))

        # Place the bet
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

        bet_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]

        # Record balance transaction
        db.execute('''
            INSERT INTO balance_transactions (amount, transaction_type, description, bet_id, created_at)
            VALUES (?, 'bet_placed', ?, ?, ?)
        ''', (-amount_to_deduct, f"{bet_type.title()} bet on {data.get('selection_name')}", bet_id,
              datetime.utcnow().isoformat() + 'Z'))

        db.commit()

        return jsonify({
            "success": True,
            "message": "Bet placed successfully",
            "bet_id": bet_id,
            "new_balance": new_balance
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
# BALANCE MANAGEMENT ENDPOINTS
# ============================================================

@app.route('/api/balance', methods=['GET'])
def get_balance():
    """Get current user balance."""
    db = get_db()
    balance = db.execute('SELECT * FROM user_balance ORDER BY id DESC LIMIT 1').fetchone()
    if balance:
        return jsonify({"balance": balance['balance'], "updated_at": balance['updated_at']})
    return jsonify({"balance": 1000.00, "updated_at": None})


@app.route('/api/balance/deposit', methods=['POST'])
def deposit():
    """Deposit funds to balance."""
    data = request.get_json()
    amount = float(data.get('amount', 0))
    if amount <= 0:
        return jsonify({"error": "Amount must be positive"}), 400

    db = get_db()
    current = db.execute('SELECT balance FROM user_balance ORDER BY id DESC LIMIT 1').fetchone()
    new_balance = (current['balance'] if current else 1000.00) + amount

    db.execute('UPDATE user_balance SET balance = ?, updated_at = ?',
               (new_balance, datetime.utcnow().isoformat() + 'Z'))
    db.execute('''
        INSERT INTO balance_transactions (amount, transaction_type, description, created_at)
        VALUES (?, 'deposit', 'Deposit', ?)
    ''', (amount, datetime.utcnow().isoformat() + 'Z'))
    db.commit()

    return jsonify({"success": True, "new_balance": new_balance})


@app.route('/api/balance/withdraw', methods=['POST'])
def withdraw():
    """Withdraw funds from balance."""
    data = request.get_json()
    amount = float(data.get('amount', 0))
    if amount <= 0:
        return jsonify({"error": "Amount must be positive"}), 400

    db = get_db()
    current = db.execute('SELECT balance FROM user_balance ORDER BY id DESC LIMIT 1').fetchone()
    current_balance = current['balance'] if current else 1000.00

    if amount > current_balance:
        return jsonify({"error": "Insufficient balance"}), 400

    new_balance = current_balance - amount
    db.execute('UPDATE user_balance SET balance = ?, updated_at = ?',
               (new_balance, datetime.utcnow().isoformat() + 'Z'))
    db.execute('''
        INSERT INTO balance_transactions (amount, transaction_type, description, created_at)
        VALUES (?, 'withdrawal', 'Withdrawal', ?)
    ''', (-amount, datetime.utcnow().isoformat() + 'Z'))
    db.commit()

    return jsonify({"success": True, "new_balance": new_balance})


@app.route('/api/balance/transactions', methods=['GET'])
def get_transactions():
    """Get balance transaction history."""
    db = get_db()
    transactions = db.execute('''
        SELECT * FROM balance_transactions
        ORDER BY created_at DESC
        LIMIT 50
    ''').fetchall()
    return jsonify([dict(t) for t in transactions])


# ============================================================
# BET RESOLUTION ENDPOINTS
# ============================================================

@app.route('/api/bets/settle/<int:bet_id>', methods=['POST'])
def settle_bet(bet_id):
    """Manually settle a bet (for testing or admin use)."""
    data = request.get_json()
    result = data.get('result')  # 'won' or 'lost'

    if result not in ['won', 'lost']:
        return jsonify({"error": "Result must be 'won' or 'lost'"}), 400

    db = get_db()
    bet = db.execute('SELECT * FROM user_bets WHERE id = ?', (bet_id,)).fetchone()

    if not bet:
        return jsonify({"error": "Bet not found"}), 404

    if bet['status'] != 'open':
        return jsonify({"error": "Bet already settled"}), 400

    # Calculate profit/loss
    stake = bet['stake']
    odds = bet['odds']
    bet_type = bet['bet_type']

    if result == 'won':
        if bet_type == 'back':
            profit_loss = stake * (odds - 1)  # Net profit (stake is returned)
        else:  # lay
            profit_loss = stake  # Liability was risked, stake is profit
    else:  # lost
        if bet_type == 'back':
            profit_loss = -stake  # Lost stake
        else:  # lay
            profit_loss = -(stake * (odds - 1))  # Lost liability

    # Update bet
    db.execute('''
        UPDATE user_bets
        SET status = 'settled', result = ?, settled_at = ?, profit_loss = ?
        WHERE id = ?
    ''', (result, datetime.utcnow().isoformat() + 'Z', profit_loss, bet_id))

    # Update balance
    current = db.execute('SELECT balance FROM user_balance ORDER BY id DESC LIMIT 1').fetchone()
    new_balance = current['balance'] + profit_loss + (stake if result == 'won' and bet_type == 'back' else 0)
    # For back bets that won, return stake + profit
    # For lay bets that won, profit only (stake was never deducted)
    # For lost bets, no return

    if result == 'won':
        if bet_type == 'back':
            balance_change = stake * odds  # Stake + winnings
        else:
            balance_change = stake  # Just the profit (liability release is neutral)
    else:
        balance_change = 0  # Already deducted when bet was placed

    current_balance = current['balance'] if current else 1000.00
    new_balance = current_balance + balance_change

    db.execute('UPDATE user_balance SET balance = ?, updated_at = ?',
               (new_balance, datetime.utcnow().isoformat() + 'Z'))

    # Record transaction
    db.execute('''
        INSERT INTO balance_transactions (amount, transaction_type, description, bet_id, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (balance_change, 'bet_settlement',
          f"{'Won' if result == 'won' else 'Lost'} bet on {bet['selection_name']}",
          bet_id, datetime.utcnow().isoformat() + 'Z'))

    db.commit()

    return jsonify({
        "success": True,
        "bet_id": bet_id,
        "result": result,
        "profit_loss": profit_loss,
        "new_balance": new_balance
    })


@app.route('/api/bets/stats', methods=['GET'])
def get_bet_stats():
    """Get betting statistics."""
    db = get_db()

    total_bets = db.execute('SELECT COUNT(*) as count FROM user_bets').fetchone()['count']
    open_bets = db.execute("SELECT COUNT(*) as count FROM user_bets WHERE status = 'open'").fetchone()['count']
    won_bets = db.execute("SELECT COUNT(*) as count FROM user_bets WHERE result = 'won'").fetchone()['count']
    lost_bets = db.execute("SELECT COUNT(*) as count FROM user_bets WHERE result = 'lost'").fetchone()['count']

    total_staked = db.execute('SELECT COALESCE(SUM(stake), 0) as total FROM user_bets').fetchone()['total']
    total_profit = db.execute(
        "SELECT COALESCE(SUM(profit_loss), 0) as total FROM user_bets WHERE status = 'settled'"
    ).fetchone()['total']

    return jsonify({
        "total_bets": total_bets,
        "pending": open_bets,
        "won": won_bets,
        "lost": lost_bets,
        "win_rate": round(won_bets / (won_bets + lost_bets) * 100, 1) if (won_bets + lost_bets) > 0 else 0,
        "total_staked": total_staked,
        "net_profit_loss": total_profit
    })


@app.route('/api/bets/check-results', methods=['POST'])
def check_bet_results():
    """
    Check for completed events and determine which bets can be settled.
    In a production system, this would query an external API for match results.
    For now, it identifies bets on events that have passed their start time.
    """
    db = get_db()

    # Find open bets on events that have likely ended (start_time > 2 hours ago)
    two_hours_ago = (datetime.utcnow() - timedelta(hours=2)).isoformat() + 'Z'

    pending_bets = db.execute('''
        SELECT b.id, b.event_id, b.selection_name, b.bet_type, b.odds, b.stake,
               e.event_name, e.sport, e.start_time, e.status as event_status
        FROM user_bets b
        JOIN scraped_events e ON b.event_id = e.id
        WHERE b.status = 'open'
        AND e.start_time IS NOT NULL
        AND e.start_time < ?
    ''', (two_hours_ago,)).fetchall()

    pending_list = [dict(b) for b in pending_bets]

    return jsonify({
        "pending_bets_count": len(pending_list),
        "pending_bets": pending_list,
        "message": "These bets are on events that have likely finished. Use /api/bets/settle/<id> to settle them."
    })


@app.route('/api/bets/history', methods=['GET'])
def get_bet_history():
    """Get full bet history with results."""
    db = get_db()
    bets = db.execute('''
        SELECT b.id, b.event_id, b.selection_name, b.bet_type, b.odds, b.stake,
               b.potential_return, b.status, b.result, b.settled_at, b.profit_loss,
               b.created_at as placed_at,
               e.event_name, e.sport, e.start_time as event_start_time
        FROM user_bets b
        LEFT JOIN scraped_events e ON b.event_id = e.id
        ORDER BY b.created_at DESC
    ''').fetchall()
    return jsonify({"bets": [dict(b) for b in bets]})


# ============================================================
# AI BET FEED ENDPOINTS
# ============================================================

@app.route('/api/ai/bet-feed', methods=['GET'])
def get_ai_bet_feed():
    """
    Return the most recent AI-analyzed value bet recommendations.
    Auto-generates if recommendations are empty or stale (>30 min old).
    """
    db = get_db()

    # Check if we need to generate recommendations
    latest = db.execute('''
        SELECT created_at FROM ai_recommendations ORDER BY created_at DESC LIMIT 1
    ''').fetchone()

    need_generation = False
    if not latest:
        need_generation = True
    else:
        # Check if recommendations are stale (>30 min)
        try:
            latest_time = datetime.fromisoformat(latest['created_at'].replace('Z', '+00:00'))
            age_minutes = (datetime.now(latest_time.tzinfo) - latest_time).total_seconds() / 60
            if age_minutes > 30:
                need_generation = True
        except:
            pass

    # Check if we have events to analyze
    event_count = db.execute('SELECT COUNT(*) as cnt FROM scraped_events WHERE data_type = ?', ('exchange',)).fetchone()

    # Auto-generate if needed and we have events
    if need_generation and event_count and event_count['cnt'] > 0:
        try:
            print("Auto-generating AI recommendations for bet feed...", flush=True)
            run_ai_analysis()
            print("Auto-generation complete", flush=True)
        except Exception as e:
            print(f"Auto-generation error: {e}", flush=True)

    # Get recommendations
    recommendations = db.execute('''
        SELECT r.*, e.is_live
        FROM ai_recommendations r
        LEFT JOIN scraped_events e ON r.event_id = e.id
        ORDER BY r.created_at DESC
        LIMIT 10
    ''').fetchall()

    # Get updated timestamp
    latest = db.execute('''
        SELECT created_at FROM ai_recommendations ORDER BY created_at DESC LIMIT 1
    ''').fetchone()

    result = []
    for rec in recommendations:
        result.append({
            'event_id': rec['event_id'],
            'sport': rec['sport'],
            'competition': rec['competition'],
            'side': rec['selection'],
            'opponent': rec['opponent'],
            'odds': rec['odds'],
            'stake': rec['stake'],
            'reason': rec['reason'],
            'text': f"£{rec['stake']} on {rec['selection']} vs {rec['opponent']}",
            'is_live': rec['is_live'] if rec['is_live'] else 0
        })

    return jsonify({
        "recommendations": result,
        "generated_at": latest['created_at'] if latest else None,
        "source": "opus_4.5_analysis"
    })


@app.route('/api/ai/analyze-bets', methods=['POST'])
def analyze_bets_with_ai():
    """
    Use Opus 4.5 to analyze all current matches and odds,
    then generate value bet recommendations with reasons.
    Called automatically after each scrape.
    """
    import anthropic
    import json

    db = get_db()

    # Get all events with odds
    events = db.execute('''
        SELECT e.id, e.event_name, e.sport, e.competition, e.start_time, e.is_live
        FROM scraped_events e
        WHERE e.data_type = 'exchange'
        ORDER BY e.scrape_order ASC
        LIMIT 50
    ''').fetchall()

    if not events:
        return jsonify({"success": False, "message": "No events to analyze"})

    # Build odds data for each event
    matches_data = []
    for event in events:
        odds = db.execute('''
            SELECT selection_name, back_odds, lay_odds
            FROM scraped_odds
            WHERE event_id = ?
        ''', (event['id'],)).fetchall()

        if odds:
            matches_data.append({
                'event_id': event['id'],
                'event_name': event['event_name'],
                'sport': event['sport'],
                'competition': event['competition'],
                'start_time': event['start_time'],
                'is_live': event['is_live'],
                'odds': [{'selection': o['selection_name'], 'back': o['back_odds'], 'lay': o['lay_odds']} for o in odds]
            })

    if not matches_data:
        return jsonify({"success": False, "message": "No odds data available"})

    # Call Opus 4.5 for analysis
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return jsonify({"success": False, "error": "ANTHROPIC_API_KEY not set"}), 500

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""You are a professional sports betting analyst. Analyze these matches and their exchange odds to find VALUE BETS.

MATCHES AND ODDS:
{json.dumps(matches_data, indent=2)}

TASK: Identify 5-8 value bets from these matches. Consider:
- Odds that seem mispriced (implied probability vs likely outcome)
- Strong favorites at good prices
- Slight underdogs with good form potential
- Avoid draws unless exceptional value

For each recommendation, provide:
1. The selection to back
2. The opponent
3. The odds
4. Recommended stake (£2-10 based on confidence)
5. A SHORT reason (12 words max) explaining WHY this bet has value

RESPOND IN THIS EXACT JSON FORMAT:
{{
  "recommendations": [
    {{
      "event_id": <number>,
      "event_name": "<match name>",
      "sport": "<sport>",
      "competition": "<competition>",
      "selection": "<team/player to back>",
      "opponent": "<opposing team/player>",
      "odds": <decimal odds>,
      "stake": <2-10>,
      "reason": "<12 words max explaining value>"
    }}
  ]
}}

IMPORTANT: reason must be 12 words or less. Be specific about why it's value.
You MAY use web_search to research team form, injuries, or news to inform your analysis."""

    # Web search tool for researching team form, injuries, news
    web_search_tool = {
        "type": "web_search_20250305",
        "name": "web_search",
        "max_uses": 5
    }

    try:
        response = client.messages.create(
            model="claude-opus-4-5-20251101",
            max_tokens=4000,
            tools=[web_search_tool],
            messages=[{"role": "user", "content": prompt}]
        )

        # Extract JSON from response - may be in text blocks after tool use
        response_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                response_text += block.text

        # Find JSON in response
        import re
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if not json_match:
            return jsonify({"success": False, "error": "No JSON in AI response"})

        analysis = json.loads(json_match.group())
        recs = analysis.get('recommendations', [])

        # Clear old recommendations and save new ones
        db.execute('DELETE FROM ai_recommendations')

        timestamp = datetime.utcnow().isoformat() + 'Z'
        for rec in recs:
            db.execute('''
                INSERT INTO ai_recommendations
                (event_id, event_name, sport, competition, selection, opponent, odds, stake, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                rec.get('event_id'),
                rec.get('event_name', ''),
                rec.get('sport', 'football'),
                rec.get('competition', ''),
                rec.get('selection', ''),
                rec.get('opponent', ''),
                rec.get('odds', 0),
                rec.get('stake', 5),
                rec.get('reason', '')[:100],  # Truncate to 100 chars max
                timestamp
            ))

        db.commit()

        return jsonify({
            "success": True,
            "recommendations_count": len(recs),
            "model": "claude-opus-4-5-20251101",
            "analyzed_at": timestamp
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# GEMINI DEEP RESEARCH ENDPOINT (Streaming with Progress)
# ============================================================

@app.route('/api/ai/deep-research/<int:event_id>', methods=['POST'])
def deep_research(event_id):
    """
    Run Gemini deep research agent on a match with streaming progress.
    Uses google-genai deep-research-pro agent.
    Cost: ~£2 per research query (deducted from balance).
    Returns Server-Sent Events for real-time progress updates.
    """
    from flask import Response, stream_with_context
    import time as time_module
    import json as json_module

    db = get_db()

    # Get event data from request body (more reliable than DB lookup)
    request_data = request.get_json() or {}
    event_from_request = request_data.get('event')

    # Try DB first
    event = db.execute('''
        SELECT e.*, GROUP_CONCAT(o.selection_name || ':' || COALESCE(o.back_odds, 0) || ':' || COALESCE(o.lay_odds, 0)) as odds_str
        FROM scraped_events e
        LEFT JOIN scraped_odds o ON e.id = o.event_id
        WHERE e.id = ?
        GROUP BY e.id
    ''', (event_id,)).fetchone()

    # Fall back to request data if DB lookup fails
    if not event and not event_from_request:
        return jsonify({"success": False, "error": "Event not found. Please refresh the page."}), 404

    # Check for Gemini API key
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        return jsonify({"success": False, "error": "GEMINI_API_KEY not configured"}), 500

    # Extract event details from DB or request
    if event:
        event_name = event['event_name']
        sport = event['sport']
        competition = event['competition'] or 'Unknown'
        start_time = event['start_time'] or 'Unknown'
        is_live = event['is_live'] == 1
        odds_str = event['odds_str']
    else:
        event_name = event_from_request.get('event_name', 'Unknown Match')
        sport = event_from_request.get('sport', 'Football')
        competition = event_from_request.get('competition', 'Unknown')
        start_time = event_from_request.get('start_time', 'Unknown')
        is_live = event_from_request.get('is_live', 0) == 1
        odds_str = None
        # Build odds string from request data
        if event_from_request.get('odds'):
            odds_parts = []
            for o in event_from_request['odds']:
                odds_parts.append(f"{o.get('selection', '')}:{o.get('back_odds', 0)}:{o.get('lay_odds', 0)}")
            odds_str = ','.join(odds_parts)

    today_date = datetime.utcnow().strftime('%Y-%m-%d')

    # Parse odds
    odds_info = ""
    if odds_str:
        odds_parts = odds_str.split(',')
        for part in odds_parts:
            try:
                sel, back, lay = part.split(':')
                odds_info += f"- {sel}: Back {back}, Lay {lay}\n"
            except:
                pass

    # Build comprehensive research query with all available context
    status_text = "IN-PLAY (live match)" if is_live else f"Scheduled: {start_time}"

    research_query = f"""Research and analyze this sports match for betting value on Betfair Exchange.

EVENT DETAILS:
- Match: {event_name}
- Sport: {sport}
- Competition: {competition}
- Status: {status_text}
- Research Date: {today_date}

CURRENT BETFAIR EXCHANGE ODDS:
{odds_info if odds_info else "No odds available yet"}

RESEARCH REQUIREMENTS:
Please provide comprehensive research covering:

1. TEAM/PLAYER FORM
   - Last 5-10 match results for each team/player
   - Goals/points scored and conceded
   - Home vs away form differences

2. HEAD-TO-HEAD RECORD
   - Recent meetings between these teams/players
   - Historical patterns in this matchup

3. SQUAD/PLAYER NEWS
   - Key injuries, suspensions, or absences
   - Expected lineups/starting formations
   - Recent transfers or returning players

4. COMPETITION CONTEXT
   - Current standings in {competition}
   - Historical performance in this competition
   - Motivation factors (title race, relegation, etc.)

5. EXTERNAL FACTORS
   - Weather conditions if relevant (outdoor sports)
   - Travel distance and fixture congestion
   - Referee/official assignments if available

6. VALUE ASSESSMENT
   - Compare current odds to implied probabilities
   - Identify potential value bets (odds too high/low)
   - Risk assessment for each betting option

Please provide specific statistics, dates, and cite your sources. Focus on information relevant to {today_date} and this specific matchup."""

    def generate_sse():
        """Generator function for Server-Sent Events streaming."""
        try:
            from google import genai

            # Initialize Gemini client
            client = genai.Client(api_key=gemini_key)

            # Send initial progress updates
            yield f"data: {json_module.dumps({'type': 'progress', 'message': 'Starting deep research...', 'icon': 'search', 'step': 1})}\n\n"
            yield f"data: {json_module.dumps({'type': 'progress', 'message': f'Analyzing: {event_name}', 'icon': 'target', 'step': 2})}\n\n"

            print(f"Starting Gemini deep research for event {event_id}: {event_name}", flush=True)

            # Start the research task
            yield f"data: {json_module.dumps({'type': 'progress', 'message': 'Connecting to Gemini Deep Research...', 'icon': 'brain', 'step': 3})}\n\n"

            interaction = client.interactions.create(
                agent="deep-research-pro-preview-12-2025",
                input=research_query,
                background=True
            )

            # Poll for results with progress updates
            progress_messages = [
                ('Searching for recent match results...', 'chart', 4),
                ('Analyzing team form and statistics...', 'trending', 5),
                ('Checking injury reports and team news...', 'alert', 6),
                ('Reviewing head-to-head records...', 'users', 7),
                ('Examining competition standings...', 'trophy', 8),
                ('Evaluating betting value...', 'dollar', 9),
                ('Compiling research findings...', 'file', 10),
            ]

            max_wait = 300  # 5 minutes
            poll_interval = 8  # 8 seconds
            elapsed = 0
            msg_index = 0
            result_text = None

            while elapsed < max_wait:
                time_module.sleep(poll_interval)
                elapsed += poll_interval

                # Send progress update
                if msg_index < len(progress_messages):
                    msg, icon, step = progress_messages[msg_index]
                    yield f"data: {json_module.dumps({'type': 'progress', 'message': msg, 'icon': icon, 'step': step})}\n\n"
                    msg_index += 1

                # Check status
                try:
                    status = client.interactions.get(interaction.id)

                    if hasattr(status, 'outputs') and status.outputs:
                        result_text = status.outputs[-1].text
                        break
                    elif hasattr(status, 'status'):
                        if status.status == 'completed':
                            if hasattr(status, 'outputs') and status.outputs:
                                result_text = status.outputs[-1].text
                            break
                        elif status.status == 'failed':
                            yield f"data: {json_module.dumps({'type': 'error', 'message': 'Research failed. Please try again.'})}\n\n"
                            return
                except Exception as poll_err:
                    print(f"  Polling error: {poll_err}", flush=True)

                print(f"  Deep research polling... {elapsed}s elapsed", flush=True)

            if not result_text:
                yield f"data: {json_module.dumps({'type': 'error', 'message': 'Research timed out. The match may be too obscure for deep analysis.'})}\n\n"
                return

            yield f"data: {json_module.dumps({'type': 'progress', 'message': 'Research complete! Preparing results...', 'icon': 'check', 'step': 11})}\n\n"

            # Save to database
            timestamp = datetime.utcnow().isoformat() + 'Z'
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO ai_conversations (created_at, conversation_type, event_id, event_name)
                VALUES (?, 'deep_research', ?, ?)
            ''', (timestamp, event_id, event_name))
            conn.commit()
            conv_id = cursor.lastrowid

            cursor.execute('''
                INSERT INTO ai_messages (conversation_id, role, content, model_used, response_source, created_at)
                VALUES (?, 'user', ?, 'gemini-deep-research', 'gemini_api', ?)
            ''', (conv_id, research_query, timestamp))

            cursor.execute('''
                INSERT INTO ai_messages (conversation_id, role, content, model_used, response_source, created_at)
                VALUES (?, 'assistant', ?, 'gemini-deep-research-pro', 'gemini_api', ?)
            ''', (conv_id, result_text, timestamp))
            conn.commit()
            conn.close()

            print(f"Deep research complete for event {event_id}", flush=True)

            # Send final result
            yield f"data: {json_module.dumps({'type': 'complete', 'research': result_text, 'conversation_id': conv_id, 'model': 'gemini-deep-research-pro', 'event_name': event_name})}\n\n"

        except ImportError:
            yield f"data: {json_module.dumps({'type': 'error', 'message': 'Gemini API not configured. Contact support.'})}\n\n"
        except Exception as e:
            print(f"Deep research error: {e}", flush=True)
            import traceback
            traceback.print_exc()
            yield f"data: {json_module.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return Response(
        stream_with_context(generate_sse()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


@app.route('/api/ai/deep-research/history/<int:event_id>', methods=['GET'])
def get_deep_research_history(event_id):
    """Get all deep research results for an event."""
    db = get_db()

    conversations = db.execute('''
        SELECT c.id, c.created_at, c.event_name
        FROM ai_conversations c
        WHERE c.conversation_type = 'deep_research'
        AND c.event_id = ?
        ORDER BY c.created_at DESC
    ''', (event_id,)).fetchall()

    result = []
    for conv in conversations:
        messages = db.execute('''
            SELECT role, content, model_used, created_at
            FROM ai_messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
        ''', (conv['id'],)).fetchall()

        # Get the research result (assistant message)
        research_content = None
        for msg in messages:
            if msg['role'] == 'assistant':
                research_content = msg['content']
                break

        result.append({
            'id': conv['id'],
            'created_at': conv['created_at'],
            'event_name': conv['event_name'],
            'research': research_content
        })

    return jsonify({
        "event_id": event_id,
        "results": result,
        "count": len(result)
    })


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
    context = data.get('context')  # Event context for Match Intelligence

    if not message:
        return jsonify({"error": "Message is required"}), 400

    db = get_db()

    # Create or get conversation
    if not conversation_id:
        # Determine conversation type based on context
        conversation_type = 'match_intelligence' if context and context.get('event_id') else 'general'
        event_id = context.get('event_id') if context else None
        event_name = context.get('event_name') if context else None

        db.execute(
            'INSERT INTO ai_conversations (created_at, conversation_type, event_id, event_name) VALUES (?, ?, ?, ?)',
            (datetime.utcnow().isoformat() + 'Z', conversation_type, event_id, event_name)
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
        result = client.chat(message, conversation_history, context=context)

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


@app.route('/api/ai/match-intelligence', methods=['GET'])
def get_match_intelligence_logs():
    """
    Get all match intelligence conversation logs.
    Returns conversations with their messages for match analysis queries.
    """
    db = get_db()

    # Get all match intelligence conversations with their messages
    conversations = db.execute('''
        SELECT c.id, c.created_at, c.event_id, c.event_name,
               e.sport, e.competition
        FROM ai_conversations c
        LEFT JOIN scraped_events e ON c.event_id = e.id
        WHERE c.conversation_type = 'match_intelligence'
        ORDER BY c.created_at DESC
        LIMIT 50
    ''').fetchall()

    result = []
    for conv in conversations:
        # Get messages for this conversation
        messages = db.execute('''
            SELECT role, content, model_used, created_at
            FROM ai_messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
        ''', (conv['id'],)).fetchall()

        result.append({
            'id': conv['id'],
            'created_at': conv['created_at'],
            'event_id': conv['event_id'],
            'event_name': conv['event_name'],
            'sport': conv['sport'],
            'competition': conv['competition'],
            'messages': [dict(m) for m in messages]
        })

    return jsonify({
        "logs": result,
        "count": len(result)
    })


@app.route('/api/ai/match-intelligence/<int:event_id>', methods=['GET'])
def get_match_intelligence_for_event(event_id):
    """Get all match intelligence conversations for a specific event."""
    db = get_db()

    # Get conversations for this event
    conversations = db.execute('''
        SELECT c.id, c.created_at, c.event_name
        FROM ai_conversations c
        WHERE c.conversation_type = 'match_intelligence'
        AND c.event_id = ?
        ORDER BY c.created_at DESC
    ''', (event_id,)).fetchall()

    result = []
    for conv in conversations:
        messages = db.execute('''
            SELECT role, content, model_used, created_at
            FROM ai_messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
        ''', (conv['id'],)).fetchall()

        result.append({
            'id': conv['id'],
            'created_at': conv['created_at'],
            'event_name': conv['event_name'],
            'messages': [dict(m) for m in messages]
        })

    return jsonify({
        "event_id": event_id,
        "logs": result,
        "count": len(result)
    })


# ============================================================
# SCHEDULER SETUP
# ============================================================

def scheduled_scrape():
    """Run exchange scrape on schedule, then analyze with Opus 4.5."""
    from exchange_scraper import run_exchange_scrape

    print(f"[{datetime.utcnow().isoformat()}] Running scheduled exchange scrape...")
    try:
        with app.app_context():
            # Run exchange scrape only
            ex_result = run_exchange_scrape()
            total = ex_result.get('total', 0) if ex_result else 0
            print(f"  Exchange: {total} events")

            scraper_status["last_scrape"] = datetime.utcnow().isoformat() + 'Z'
            scraper_status["events_count"] = {
                "exchange": (ex_result or {}).get("counts", {})
            }
            print(f"Scheduled scrape complete: {total} total events")

            # Run Opus 4.5 analysis after scrape
            if total > 0:
                print("Running Opus 4.5 value bet analysis...")
                try:
                    run_ai_analysis()
                    print("Opus 4.5 analysis complete")
                except Exception as ai_err:
                    print(f"AI analysis error: {ai_err}")
    except Exception as e:
        print(f"Scheduled scrape error: {e}")


def run_ai_analysis():
    """Run Opus 4.5 analysis on current matches."""
    import anthropic
    import json

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all events with odds
    cursor.execute('''
        SELECT e.id, e.event_name, e.sport, e.competition, e.start_time, e.is_live
        FROM scraped_events e
        WHERE e.data_type = 'exchange'
        ORDER BY e.scrape_order ASC
        LIMIT 50
    ''')
    events = cursor.fetchall()

    if not events:
        conn.close()
        return

    # Build odds data for each event
    matches_data = []
    for event in events:
        cursor.execute('''
            SELECT selection_name, back_odds, lay_odds
            FROM scraped_odds
            WHERE event_id = ?
        ''', (event['id'],))
        odds = cursor.fetchall()

        if odds:
            matches_data.append({
                'event_id': event['id'],
                'event_name': event['event_name'],
                'sport': event['sport'],
                'competition': event['competition'],
                'start_time': event['start_time'],
                'is_live': event['is_live'],
                'odds': [{'selection': o['selection_name'], 'back': o['back_odds'], 'lay': o['lay_odds']} for o in odds]
            })

    if not matches_data:
        conn.close()
        return

    # Call Opus 4.5 for analysis
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        conn.close()
        return

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""You are a professional sports betting analyst. Analyze these matches and their exchange odds to find VALUE BETS.

MATCHES AND ODDS:
{json.dumps(matches_data, indent=2)}

TASK: Identify 5-8 value bets from these matches. Consider:
- Odds that seem mispriced (implied probability vs likely outcome)
- Strong favorites at good prices
- Slight underdogs with good form potential
- Avoid draws unless exceptional value

For each recommendation, provide:
1. The selection to back
2. The opponent
3. The odds
4. Recommended stake (£2-10 based on confidence)
5. A SHORT reason (12 words max) explaining WHY this bet has value

RESPOND IN THIS EXACT JSON FORMAT:
{{
  "recommendations": [
    {{
      "event_id": <number>,
      "event_name": "<match name>",
      "sport": "<sport>",
      "competition": "<competition>",
      "selection": "<team/player to back>",
      "opponent": "<opposing team/player>",
      "odds": <decimal odds>,
      "stake": <2-10>,
      "reason": "<12 words max explaining value>"
    }}
  ]
}}

IMPORTANT: reason must be 12 words or less. Be specific about why it's value.
You MAY use web_search to research team form, injuries, or news to inform your analysis."""

    # Web search tool for researching team form, injuries, news
    web_search_tool = {
        "type": "web_search_20250305",
        "name": "web_search",
        "max_uses": 5
    }

    try:
        response = client.messages.create(
            model="claude-opus-4-5-20251101",
            max_tokens=4000,
            tools=[web_search_tool],
            messages=[{"role": "user", "content": prompt}]
        )

        # Extract JSON from response - may be in text blocks after tool use
        response_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                response_text += block.text

        # Find JSON in response
        import re
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if not json_match:
            conn.close()
            return

        analysis = json.loads(json_match.group())
        recs = analysis.get('recommendations', [])

        # Clear old recommendations and save new ones
        cursor.execute('DELETE FROM ai_recommendations')

        timestamp = datetime.utcnow().isoformat() + 'Z'
        for rec in recs:
            cursor.execute('''
                INSERT INTO ai_recommendations
                (event_id, event_name, sport, competition, selection, opponent, odds, stake, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                rec.get('event_id'),
                rec.get('event_name', ''),
                rec.get('sport', 'football'),
                rec.get('competition', ''),
                rec.get('selection', ''),
                rec.get('opponent', ''),
                rec.get('odds', 0),
                rec.get('stake', 5),
                rec.get('reason', '')[:100],
                timestamp
            ))

        conn.commit()
        print(f"  Saved {len(recs)} AI recommendations")

    except Exception as e:
        print(f"AI analysis error: {e}")

    conn.close()


def scheduled_bet_check():
    """
    Periodically check for bets that can be settled.
    Logs pending bets on finished events.
    """
    print(f"[{datetime.utcnow().isoformat()}] Checking for settleable bets...")
    try:
        with app.app_context():
            conn = sqlite3.connect(DATABASE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Find open bets on events that have likely ended (start_time > 2 hours ago)
            two_hours_ago = (datetime.utcnow() - timedelta(hours=2)).isoformat() + 'Z'

            cursor.execute('''
                SELECT b.id, b.selection_name, e.event_name, e.start_time
                FROM user_bets b
                JOIN scraped_events e ON b.event_id = e.id
                WHERE b.status = 'open'
                AND e.start_time IS NOT NULL
                AND e.start_time < ?
            ''', (two_hours_ago,))

            pending = cursor.fetchall()
            conn.close()

            if pending:
                print(f"Found {len(pending)} bets ready to settle:")
                for bet in pending:
                    print(f"  - Bet #{bet['id']}: {bet['selection_name']} on {bet['event_name']}")
            else:
                print("No pending bets to settle.")
    except Exception as e:
        print(f"Bet check error: {e}")


# ============================================================
# APP STARTUP
# ============================================================

# Always initialize database on module load (for gunicorn)
init_db()

def run_initial_scrape_background():
    """Run initial exchange scrape in background thread so it doesn't block startup."""
    import time
    import traceback
    time.sleep(5)  # Give the server a moment to fully start
    print("Running initial exchange scrape in background...", flush=True)
    try:
        with app.app_context():
            from exchange_scraper import run_exchange_scrape

            ex_result = run_exchange_scrape()
            total = (ex_result or {}).get('total', 0)
            print(f"  Exchange: {total} events", flush=True)

            # Run AI analysis after initial scrape if we got events
            if total > 0:
                print("Running initial AI value bet analysis...", flush=True)
                try:
                    run_ai_analysis()
                    print("Initial AI analysis complete", flush=True)
                except Exception as ai_err:
                    print(f"Initial AI analysis error: {ai_err}", flush=True)
    except Exception as e:
        print(f"Initial scrape error: {e}", flush=True)
        traceback.print_exc()

# Start scheduler for auto-refresh and bet checking (runs for both gunicorn and direct)
# Only add jobs if scheduler hasn't been configured yet
import sys

def setup_scheduler_and_scrape():
    """Initialize scheduler and run initial scrape - called once on startup."""
    try:
        if not scheduler.get_jobs():
            scheduler.add_job(
                scheduled_scrape,
                'interval',
                minutes=SCRAPE_INTERVAL_MINUTES,
                id='auto_scrape'
            )
            scheduler.add_job(
                scheduled_bet_check,
                'interval',
                minutes=30,  # Check every 30 minutes
                id='bet_check'
            )
            scheduler.start()
            print(f"Scheduler started: odds refresh every {SCRAPE_INTERVAL_MINUTES} min, bet check every 30 min", flush=True)

            # Run initial scrape in background thread (doesn't block server startup)
            import threading
            scrape_thread = threading.Thread(target=run_initial_scrape_background, daemon=True)
            scrape_thread.start()
            print("Background scrape thread started", flush=True)
    except Exception as e:
        print(f"Scheduler setup error: {e}", flush=True)

# Run setup
setup_scheduler_and_scrape()

if __name__ == '__main__':
    # Start Flask server (for local development)
    port = int(os.environ.get('PORT', 3001))
    print(f"Starting BetAI v2 backend on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
