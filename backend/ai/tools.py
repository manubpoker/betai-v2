"""
AI Tools for BetAI Claude Client

These tools allow Claude to:
1. Query the database for current events/odds
2. Trigger a live scrape from Betfair
3. Search for specific events or sports
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional

DATABASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'betai.db')


def get_db_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# Tool definitions for Claude API
TOOLS = [
    {
        "name": "query_events",
        "description": "Query betting events from the database. Use this to get current events, filter by sport, or find specific matches.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sport": {
                    "type": "string",
                    "description": "Optional sport filter (e.g., 'football', 'tennis', 'basketball', 'cricket')"
                },
                "search_term": {
                    "type": "string",
                    "description": "Optional search term to filter event names"
                },
                "live_only": {
                    "type": "boolean",
                    "description": "If true, only return live events"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of events to return (default 20)"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_event_odds",
        "description": "Get detailed odds for a specific event by ID. Use this when the user asks about specific odds for a match.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "integer",
                    "description": "The ID of the event to get odds for"
                }
            },
            "required": ["event_id"]
        }
    },
    {
        "name": "get_sports_summary",
        "description": "Get a summary of all available sports and how many events each has.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "refresh_odds",
        "description": "Trigger a live scrape from Betfair to get the latest odds. Use this when the user asks for updated/fresh odds or when data seems stale.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sport": {
                    "type": "string",
                    "description": "Optional: specific sport to refresh (leave empty for all sports)"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_data_freshness",
        "description": "Check how fresh the current data is (when it was last scraped).",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool and return the result as a string."""

    if tool_name == "query_events":
        return query_events(
            sport=tool_input.get("sport"),
            search_term=tool_input.get("search_term"),
            live_only=tool_input.get("live_only", False),
            limit=tool_input.get("limit", 20)
        )

    elif tool_name == "get_event_odds":
        return get_event_odds(tool_input.get("event_id"))

    elif tool_name == "get_sports_summary":
        return get_sports_summary()

    elif tool_name == "refresh_odds":
        return refresh_odds(tool_input.get("sport"))

    elif tool_name == "get_data_freshness":
        return get_data_freshness()

    else:
        return f"Unknown tool: {tool_name}"


def query_events(sport: Optional[str] = None, search_term: Optional[str] = None,
                 live_only: bool = False, limit: int = 20) -> str:
    """Query events from the database."""
    conn = get_db_connection()

    query = "SELECT * FROM scraped_events WHERE 1=1"
    params = []

    if sport:
        query += " AND LOWER(sport) = LOWER(?)"
        params.append(sport)

    if search_term:
        query += " AND LOWER(event_name) LIKE LOWER(?)"
        params.append(f"%{search_term}%")

    if live_only:
        query += " AND (is_live = 1 OR status = 'live')"

    query += " ORDER BY scraped_at DESC LIMIT ?"
    params.append(limit)

    events = conn.execute(query, params).fetchall()
    conn.close()

    if not events:
        return "No events found matching your criteria."

    result = f"Found {len(events)} events:\n\n"
    for e in events:
        live_badge = " [LIVE]" if e['is_live'] else ""
        time_info = f" at {e['start_time']}" if e['start_time'] else ""
        result += f"- [{e['id']}] {e['event_name']}{live_badge} ({e['sport']}, {e['competition']}){time_info}\n"

    return result


def get_event_odds(event_id: int) -> str:
    """Get odds for a specific event."""
    conn = get_db_connection()

    event = conn.execute(
        "SELECT * FROM scraped_events WHERE id = ?", (event_id,)
    ).fetchone()

    if not event:
        conn.close()
        return f"Event with ID {event_id} not found."

    odds = conn.execute(
        "SELECT * FROM scraped_odds WHERE event_id = ? ORDER BY selection_name",
        (event_id,)
    ).fetchall()
    conn.close()

    result = f"**{event['event_name']}**\n"
    result += f"Sport: {event['sport']} | Competition: {event['competition']}\n"
    result += f"Status: {'LIVE' if event['is_live'] else 'Upcoming'}"
    if event['start_time']:
        result += f" | Start: {event['start_time']}"
    result += f"\nScraped: {event['scraped_at']}\n\n"

    if odds:
        result += "Odds:\n"
        for o in odds:
            back = f"{o['back_odds']:.2f}" if o['back_odds'] else "-"
            lay = f"{o['lay_odds']:.2f}" if o['lay_odds'] else "-"
            fractional = f" ({o['back_odds_fractional']})" if o['back_odds_fractional'] else ""
            result += f"  - {o['selection_name']}: Back {back}{fractional} / Lay {lay}\n"
    else:
        result += "No odds data available for this event.\n"

    return result


def get_sports_summary() -> str:
    """Get summary of available sports."""
    conn = get_db_connection()

    sports = conn.execute('''
        SELECT sport, COUNT(*) as count,
               SUM(CASE WHEN is_live = 1 THEN 1 ELSE 0 END) as live_count
        FROM scraped_events
        GROUP BY sport
        ORDER BY count DESC
    ''').fetchall()

    total = conn.execute("SELECT COUNT(*) FROM scraped_events").fetchone()[0]
    conn.close()

    result = f"**Sports Summary** ({total} total events)\n\n"
    for s in sports:
        live_info = f" ({s['live_count']} live)" if s['live_count'] > 0 else ""
        result += f"- {s['sport'].title()}: {s['count']} events{live_info}\n"

    return result


def refresh_odds(sport: Optional[str] = None) -> str:
    """Trigger a live scrape from Betfair."""
    try:
        from scraper import run_full_scrape, scrape_sport

        if sport:
            # Scrape specific sport
            result = scrape_sport(sport)
            return f"Refreshed odds for {sport}. Found {len(result)} events."
        else:
            # Full scrape
            result = run_full_scrape()
            total = result.get("total", 0)
            counts = result.get("counts", {})

            response = f"Refreshed all odds. Total: {total} events.\n"
            for s, c in counts.items():
                response += f"  - {s}: {c} events\n"
            return response

    except Exception as e:
        return f"Error refreshing odds: {str(e)}"


def get_data_freshness() -> str:
    """Check data freshness."""
    conn = get_db_connection()

    newest = conn.execute('''
        SELECT scraped_at FROM scraped_events
        ORDER BY scraped_at DESC LIMIT 1
    ''').fetchone()

    oldest = conn.execute('''
        SELECT scraped_at FROM scraped_events
        ORDER BY scraped_at ASC LIMIT 1
    ''').fetchone()

    total = conn.execute("SELECT COUNT(*) FROM scraped_events").fetchone()[0]
    conn.close()

    if not newest:
        return "No data in database. Consider triggering a refresh."

    newest_time = datetime.fromisoformat(newest['scraped_at'].replace('Z', '+00:00'))
    oldest_time = datetime.fromisoformat(oldest['scraped_at'].replace('Z', '+00:00'))
    now = datetime.now(newest_time.tzinfo)

    newest_age = (now - newest_time).total_seconds() / 60
    oldest_age = (now - oldest_time).total_seconds() / 60

    freshness = "Fresh" if newest_age < 15 else "Moderate" if newest_age < 30 else "Stale"

    result = f"**Data Freshness: {freshness}**\n\n"
    result += f"- Newest data: {round(newest_age, 1)} minutes ago\n"
    result += f"- Oldest data: {round(oldest_age, 1)} minutes ago\n"
    result += f"- Total events: {total}\n"

    if newest_age > 15:
        result += "\nConsider using refresh_odds to get the latest data."

    return result
