#!/bin/bash

# Script to start the agent service
# Usage: ./start.sh

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found. Please create it first:"
    echo "  python3 -m venv venv"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "Please edit .env and add your OPENAI_API_KEY and BACKEND_URL"
    else
        echo "Error: .env.example not found. Please create .env manually."
        exit 1
    fi
fi

# Start the agent service
echo "Starting agent service on http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""
python app.py
