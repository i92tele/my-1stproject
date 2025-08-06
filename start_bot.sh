#!/bin/bash
# AutoFarming Bot Production Startup Script

echo "🚀 Starting AutoFarming Bot..."

# Activate virtual environment
source venv/bin/activate

# Set environment
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Start the bot
python3 main.py
