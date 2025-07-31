#!/bin/bash

# AutoFarming Bot Deployment Script
# This script starts all bot services with minimal human intervention

echo "🚀 Starting AutoFarming Bot Deployment..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p sessions
mkdir -p backups

# Check if .env file exists
if [ ! -f "config/.env" ]; then
    echo "❌ config/.env file not found. Please create it with your bot configuration."
    exit 1
fi

# Test configuration
echo "🔍 Testing configuration..."
python3 -c "
import sys
sys.path.append('.')
from dotenv import load_dotenv
load_dotenv('config/.env')
import config
cfg = config.BotConfig.load_from_env()
print('✅ Configuration loaded successfully')
"

if [ $? -ne 0 ]; then
    echo "❌ Configuration test failed. Please check your .env file."
    exit 1
fi

# Start all services
echo "🚀 Starting all bot services..."
python3 start_services.py

echo "✅ Deployment completed!"
echo ""
echo "📊 Services running:"
echo "• Main Bot (Telegram interface)"
echo "• Ad Scheduler (Automated posting)"
echo "• Maintenance Service (Cleanup & reports)"
echo ""
echo "📝 Logs are available in the logs/ directory"
echo "🛑 To stop all services, press Ctrl+C" 