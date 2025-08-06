#!/bin/bash
# AutoFarming Bot Environment Activation Script

if [ -d "venv" ]; then
    echo "Activating AutoFarming Bot virtual environment..."
    source venv/bin/activate
    echo "✅ Virtual environment activated!"
    echo "📝 To deactivate, run: deactivate"
    echo "🚀 To run the bot, use: python3 bot.py"
    echo "🏥 To run health checks, use: python3 quick_health_check.py"
else
    echo "❌ Virtual environment not found. Run setup.sh first."
    exit 1
fi
