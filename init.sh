#!/bin/bash

# BetAI v2 - AI-Powered Betting Platform
# Setup and initialization script

set -e

echo "========================================"
echo "  BetAI v2 - Setup Script"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

# Check for required environment variable
check_api_key() {
    if [ -z "$ANTHROPIC_API_KEY" ]; then
        echo -e "${YELLOW}WARNING: ANTHROPIC_API_KEY environment variable is not set${NC}"
        echo "AI chat features will not work without it."
        echo "Set it with: export ANTHROPIC_API_KEY=your_api_key_here"
        echo ""
    else
        echo -e "${GREEN}✓ ANTHROPIC_API_KEY is set${NC}"
    fi
}

# Check Python version
check_python() {
    echo "Checking Python installation..."
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
    else
        echo -e "${RED}✗ Python 3 is required but not installed${NC}"
        exit 1
    fi
}

# Check Node.js version
check_node() {
    echo "Checking Node.js installation..."
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        echo -e "${GREEN}✓ Node.js $NODE_VERSION found${NC}"
    else
        echo -e "${RED}✗ Node.js is required but not installed${NC}"
        exit 1
    fi
}

# Setup backend
setup_backend() {
    echo ""
    echo "Setting up backend..."
    cd "$BACKEND_DIR"

    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "Creating Python virtual environment..."
        python3 -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null

    # Install dependencies
    echo "Installing Python dependencies..."
    pip install -q --upgrade pip
    pip install -q -r requirements.txt

    # Install Playwright browsers
    echo "Installing Playwright browsers..."
    playwright install chromium

    # Initialize database
    echo "Initializing database..."
    python -c "from app import init_db; init_db()"

    echo -e "${GREEN}✓ Backend setup complete${NC}"
    cd "$PROJECT_DIR"
}

# Setup frontend
setup_frontend() {
    echo ""
    echo "Setting up frontend..."
    cd "$FRONTEND_DIR"

    # Install dependencies
    echo "Installing Node.js dependencies..."
    npm install

    echo -e "${GREEN}✓ Frontend setup complete${NC}"
    cd "$PROJECT_DIR"
}

# Start development servers
start_servers() {
    echo ""
    echo "========================================"
    echo "  Starting Development Servers"
    echo "========================================"

    # Start backend in background
    echo "Starting backend server (port 3001)..."
    cd "$BACKEND_DIR"
    source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
    python app.py &
    BACKEND_PID=$!
    cd "$PROJECT_DIR"

    # Wait for backend to be ready
    echo "Waiting for backend to start..."
    sleep 3

    # Start frontend
    echo "Starting frontend server (port 5173)..."
    cd "$FRONTEND_DIR"
    npm run dev &
    FRONTEND_PID=$!
    cd "$PROJECT_DIR"

    # Wait for frontend to be ready
    sleep 3

    echo ""
    echo "========================================"
    echo -e "${GREEN}  Servers are running!${NC}"
    echo "========================================"
    echo ""
    echo "  Frontend:  http://localhost:5173"
    echo "  Backend:   http://localhost:3001"
    echo ""
    echo "  API Verification Endpoints:"
    echo "    - http://localhost:3001/api/verify/scrape-source"
    echo "    - http://localhost:3001/api/verify/ai-status"
    echo "    - http://localhost:3001/api/verify/data-freshness"
    echo ""
    echo "  Press Ctrl+C to stop servers"
    echo ""

    # Wait for interrupt
    trap "echo 'Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT
    wait
}

# Run initial scrape
run_initial_scrape() {
    echo ""
    echo "Running initial data scrape..."
    cd "$BACKEND_DIR"
    source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
    python -c "from scraper import run_full_scrape; run_full_scrape()" || echo -e "${YELLOW}Initial scrape skipped (will run when server starts)${NC}"
    cd "$PROJECT_DIR"
}

# Main execution
main() {
    echo ""

    # Check requirements
    check_api_key
    check_python
    check_node

    # Setup if needed
    if [ ! -d "$BACKEND_DIR/venv" ] || [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        echo ""
        echo "First time setup detected. Installing dependencies..."
        setup_backend
        setup_frontend
    else
        echo -e "${GREEN}✓ Dependencies already installed${NC}"
    fi

    # Start servers
    start_servers
}

# Run only setup (no servers)
if [ "$1" == "--setup-only" ]; then
    check_api_key
    check_python
    check_node
    setup_backend
    setup_frontend
    echo ""
    echo -e "${GREEN}Setup complete!${NC}"
    echo "Run './init.sh' again to start the servers."
    exit 0
fi

# Run scrape only
if [ "$1" == "--scrape" ]; then
    check_python
    run_initial_scrape
    exit 0
fi

main
