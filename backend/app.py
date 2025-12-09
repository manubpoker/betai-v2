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
    Manually trigger a scrape.
    Query param: data_type = 'sportsbook', 'exchange', or 'both' (default)
    """
    from scraper import run_full_scrape as run_sportsbook_scrape
    from exchange_scraper import run_exchange_scrape

    data_type = request.args.get('data_type', 'both')

    try:
        scraper_status["status"] = "running"
        results = {"sportsbook": None, "exchange": None}
        total = 0

        # Run sportsbook scraper
        if data_type in ('both', 'sportsbook'):
            sb_result = run_sportsbook_scrape()
            results["sportsbook"] = sb_result
            total += sb_result.get("total", 0)

        # Run exchange scraper
        if data_type in ('both', 'exchange'):
            ex_result = run_exchange_scrape()
            results["exchange"] = ex_result
            total += ex_result.get("total", 0)

        scraper_status["status"] = "idle"
        scraper_status["last_scrape"] = datetime.utcnow().isoformat() + 'Z'
        scraper_status["events_count"] = {
            "sportsbook": results.get("sportsbook", {}).get("counts", {}),
            "exchange": results.get("exchange", {}).get("counts", {})
        }

        return jsonify({
            "success": True,
            "message": f"Scrape completed ({data_type})",
            "events_scraped": total,
            "sportsbook": results.get("sportsbook"),
            "exchange": results.get("exchange")
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
    """Get all events, optionally filtered by sport and data_type."""
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

    events = db.execute(f'''
        SELECT * FROM scraped_events
        WHERE {where_clause}
        ORDER BY sport, start_time ASC
    ''', params).fetchall()

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
    Generate AI bet recommendations from current odds data.
    Returns back-only recommendations for events with best value.
    Format: "Recommendation: £X on [side] vs {opponent}"
    """
    import random

    db = get_db()

    # Get all events with odds
    events = db.execute('''
        SELECT e.id, e.event_name, e.sport, e.competition, e.start_time,
               o.selection_name, o.back_odds
        FROM scraped_events e
        JOIN scraped_odds o ON e.id = o.event_id
        WHERE o.back_odds IS NOT NULL AND o.back_odds > 1.0
        ORDER BY e.sport, o.back_odds ASC
    ''').fetchall()

    if not events:
        return jsonify({"recommendations": [], "message": "No events with odds available"})

    # Group by event to get both sides
    event_odds = {}
    for row in events:
        event_id = row['id']
        if event_id not in event_odds:
            event_odds[event_id] = {
                'event_name': row['event_name'],
                'sport': row['sport'],
                'competition': row['competition'],
                'start_time': row['start_time'],
                'selections': []
            }
        event_odds[event_id]['selections'].append({
            'name': row['selection_name'],
            'back_odds': row['back_odds']
        })

    recommendations = []

    # Generate recommendations - pick selections with reasonable odds (1.5 - 5.0)
    for event_id, event in event_odds.items():
        selections = event['selections']
        if len(selections) < 2:
            continue

        # Find selections with odds in value range (favorites to slight underdogs)
        for sel in selections:
            odds = sel['back_odds']
            if 1.3 <= odds <= 4.0:
                # Parse team names from event name
                event_name = event['event_name']
                side = sel['name']

                # Find opponent
                opponent = None
                for other in selections:
                    if other['name'] != side and other['name'].lower() != 'draw':
                        opponent = other['name']
                        break

                if opponent:
                    # Generate stake recommendation based on odds
                    if odds < 1.8:
                        stake = random.choice([5, 10])  # Favorites get smaller stakes
                    elif odds < 2.5:
                        stake = random.choice([3, 5])
                    else:
                        stake = random.choice([2, 3])  # Underdogs get smaller stakes

                    recommendations.append({
                        'event_id': event_id,
                        'sport': event['sport'],
                        'side': side,
                        'opponent': opponent,
                        'odds': odds,
                        'stake': stake,
                        'text': f"Recommendation: £{stake} on {side} vs {opponent}"
                    })

    # Shuffle and limit to top 10
    random.shuffle(recommendations)
    recommendations = recommendations[:10]

    return jsonify({
        "recommendations": recommendations,
        "generated_at": datetime.utcnow().isoformat() + 'Z'
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


# ============================================================
# SCHEDULER SETUP
# ============================================================

def scheduled_scrape():
    """Run both sportsbook and exchange scrapes on schedule."""
    from scraper import run_full_scrape as run_sportsbook_scrape
    from exchange_scraper import run_exchange_scrape

    print(f"[{datetime.utcnow().isoformat()}] Running scheduled scrape (both)...")
    try:
        with app.app_context():
            total = 0
            # Run sportsbook scrape
            sb_result = run_sportsbook_scrape()
            total += sb_result.get('total', 0)
            print(f"  Sportsbook: {sb_result.get('total', 0)} events")

            # Run exchange scrape
            ex_result = run_exchange_scrape()
            total += ex_result.get('total', 0)
            print(f"  Exchange: {ex_result.get('total', 0)} events")

            scraper_status["last_scrape"] = datetime.utcnow().isoformat() + 'Z'
            scraper_status["events_count"] = {
                "sportsbook": sb_result.get("counts", {}),
                "exchange": ex_result.get("counts", {})
            }
            print(f"Scheduled scrape complete: {total} total events")
    except Exception as e:
        print(f"Scheduled scrape error: {e}")


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

if __name__ == '__main__':

    # Start scheduler for auto-refresh and bet checking
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
    print(f"Scheduler started: odds refresh every {SCRAPE_INTERVAL_MINUTES} min, bet check every 30 min")

    # Run initial scrape (both sportsbook and exchange)
    print("Running initial scrape (both sportsbook and exchange)...")
    try:
        with app.app_context():
            from scraper import run_full_scrape as run_sportsbook_scrape
            from exchange_scraper import run_exchange_scrape

            sb_result = run_sportsbook_scrape()
            print(f"  Sportsbook: {sb_result.get('total', 0)} events")

            ex_result = run_exchange_scrape()
            print(f"  Exchange: {ex_result.get('total', 0)} events")
    except Exception as e:
        print(f"Initial scrape skipped: {e}")

    # Start Flask server
    port = int(os.environ.get('PORT', 3001))
    print(f"Starting BetAI v2 backend on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
