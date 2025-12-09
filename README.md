# BetAI v2 - AI-Powered Betting Platform

A professional betting platform that scrapes **REAL odds** from Betfair and provides AI-powered betting assistance using Claude.

## CRITICAL: This is NOT a demo with mock data

All data comes from actual Betfair pages scraped in real-time using Playwright. AI responses come directly from Claude API with no fallbacks.

## Features

- **Real-time Betfair scraping** - Live odds from 6 sports
- **AI betting assistant** - Claude-powered chat for betting advice
- **Exchange betting** - Back and lay betting with live odds
- **Sportsbook** - Fixed odds betting interface
- **Auto-refresh** - 15-minute automatic data updates

## Tech Stack

### Backend (Python)
- Flask web framework
- SQLite database
- Playwright for web scraping
- APScheduler for auto-refresh
- Anthropic SDK for Claude API

### Frontend (React)
- Vite build tool
- Tailwind CSS styling
- React Router navigation

## Quick Start

```bash
# Set your Claude API key
export ANTHROPIC_API_KEY=your_key_here

# Run setup and start servers
./init.sh
```

The application will be available at:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:3001

## Manual Setup

### Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Initialize database
python -c "from app import init_db; init_db()"

# Start server
python app.py
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Verification Endpoints

These endpoints verify the system is using real data:

| Endpoint | Purpose |
|----------|---------|
| `GET /api/verify/scrape-source` | Confirms data is from real Betfair scraping |
| `GET /api/verify/ai-status` | Confirms Claude API connection |
| `GET /api/verify/data-freshness` | Confirms data is recent (<30 min) |

## API Endpoints

### Events
- `GET /api/events` - List all events (filter by `?sport=`)
- `GET /api/events/:id` - Single event with odds
- `GET /api/events/live` - Live events only
- `GET /api/sports` - Sports list with counts

### Betting
- `POST /api/bets` - Place a bet
- `GET /api/bets` - Bet history
- `GET /api/bets/open` - Open bets

### AI Chat
- `POST /api/ai/chat` - Send message to Claude
- `GET /api/ai/conversations` - List conversations
- `GET /api/ai/conversations/:id` - Conversation history

### Scraping
- `POST /api/scrape/trigger` - Manual scrape
- `GET /api/scrape/status` - Scraper status

## Sports Scraped

1. **Football** - Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Champions League
2. **Tennis** - ATP, WTA, Grand Slams, ITF
3. **Horse Racing** - All UK/IRE meetings
4. **Basketball** - NBA, EuroLeague, NCAA
5. **Golf** - PGA, European Tour, Majors
6. **Cricket** - Test, ODI, T20, IPL

## Design System

| Element | Color |
|---------|-------|
| Primary (Betfair Gold) | `#FFB80C` |
| Secondary (Dark Navy) | `#1E1E2D` |
| Back Bet | `#72BBEF` |
| Lay Bet | `#FAA9BA` |
| Success | `#22C55E` |
| Error | `#EF4444` |
| AI Accent | `#7C3AED` |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key for AI features |

## Development

### Running Tests

```bash
# Backend tests
cd backend && pytest

# Frontend tests
cd frontend && npm test
```

### Code Style

- **Python**: snake_case, type annotations, docstrings
- **TypeScript/React**: PascalCase components, hooks in camelCase

## Project Structure

```
betai-v2/
├── backend/
│   ├── app.py              # Flask application
│   ├── requirements.txt    # Python dependencies
│   ├── scraper/
│   │   ├── base_scraper.py # Playwright base class
│   │   ├── football.py     # Football scraper
│   │   ├── tennis.py       # Tennis scraper
│   │   └── ...             # Other sports
│   ├── ai/
│   │   └── claude_client.py # Claude API client
│   └── routes/
│       ├── events.py       # Events endpoints
│       ├── bets.py         # Betting endpoints
│       └── ai.py           # AI chat endpoints
├── frontend/
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── hooks/          # Custom hooks
│   │   └── styles/         # CSS/Tailwind
│   ├── package.json
│   └── vite.config.js
├── feature_list.json       # Test cases (60-80 features)
├── init.sh                 # Setup script
└── README.md
```

## License

Proprietary - All rights reserved

---

**Built with real Betfair data and Claude AI**
