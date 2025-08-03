#!/bin/bash

echo "🛑 AutoFarming Pro - Stopping All Services"
echo "=========================================="

# Stop all Python processes related to the bot
echo "🔄 Stopping bot processes..."

# Stop main bot
pkill -f "python3 bot.py" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Stopped main bot"
else
    echo "ℹ️  Main bot was not running"
fi

# Stop scheduler
pkill -f "python3 scheduler.py" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Stopped scheduler"
else
    echo "ℹ️  Scheduler was not running"
fi

# Stop payment monitor
pkill -f "python3 payment_monitor.py" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Stopped payment monitor"
else
    echo "ℹ️  Payment monitor was not running"
fi

# Stop startup scripts
pkill -f "python3 start_bot.py" 2>/dev/null
pkill -f "python3 start_all_services.py" 2>/dev/null

# Wait a moment for processes to stop
sleep 2

# Check if any processes are still running
echo "🔍 Checking for remaining processes..."
REMAINING=$(ps aux | grep -E "(bot.py|scheduler.py|payment_monitor.py)" | grep -v grep)

if [ -z "$REMAINING" ]; then
    echo "✅ All services stopped successfully"
else
    echo "⚠️  Some processes may still be running:"
    echo "$REMAINING"
    echo "🔄 Force stopping remaining processes..."
    pkill -9 -f "bot.py" 2>/dev/null
    pkill -9 -f "scheduler.py" 2>/dev/null
    pkill -9 -f "payment_monitor.py" 2>/dev/null
    echo "✅ Force stopped all processes"
fi

echo ""
echo "🎯 All services stopped. Ready for clean startup!"
echo "💡 Run 'python3 start_bot.py' to start all services" 