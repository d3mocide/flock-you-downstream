#!/bin/bash
# FlockYou API - Start Script (Linux/Mac)
#
# Usage: ./start.sh [native|docker]
#   native - Run directly with Python (recommended for serial access)
#   docker - Run with Docker Compose

set -e

MODE="${1:-native}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=============================================="
echo "  FlockYou API Server"
echo "=============================================="

if [ "$MODE" = "docker" ]; then
    echo "Starting with Docker Compose..."
    
    if ! command -v docker &> /dev/null; then
        echo "ERROR: Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    cd "$SCRIPT_DIR"
    docker compose up -d --build
    
    echo ""
    echo "Server starting in background..."
    echo "View logs:  docker compose logs -f"
    echo "Stop:       docker compose down"
    echo ""
    echo "Dashboard:  http://localhost:5000"
    echo "API Health: http://localhost:5000/api/health"
    
else
    echo "Starting natively with Python..."
    
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        echo "ERROR: Python is not installed. Please install Python 3.11+."
        exit 1
    fi
    
    PYTHON_CMD="python3"
    if ! command -v python3 &> /dev/null; then
        PYTHON_CMD="python"
    fi
    
    cd "$SCRIPT_DIR/backend"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        $PYTHON_CMD -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    echo "Installing dependencies..."
    pip install -q -r requirements.txt
    
    echo ""
    echo "Starting server..."
    echo "Dashboard:  http://localhost:5000"
    echo "API Health: http://localhost:5000/api/health"
    echo "Press Ctrl+C to stop"
    echo ""
    
    python run.py
fi
