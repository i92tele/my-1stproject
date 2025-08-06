#!/bin/bash

# AutoFarming Bot - Complete Service Startup Script
# This script starts all bot services and monitors them

echo "🚀 Starting AutoFarming Bot Services..."

# Create logs directory if it doesn't exist
mkdir -p logs

# Function to check if a process is running
check_process() {
    local process_name=$1
    if pgrep -f "$process_name" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to start a service
start_service() {
    local service_name=$1
    local script_name=$2
    local log_file="logs/${service_name}.log"
    
    echo "📦 Starting $service_name..."
    
    # Kill existing process if running
    pkill -f "$script_name" 2>/dev/null
    sleep 2
    
    # Remove lock file if exists
    rm -f bot.lock
    
    # Start the service
    python3 "$script_name" > "$log_file" 2>&1 &
    
    # Wait a moment and check if it started
    sleep 3
    if check_process "$script_name"; then
        echo "✅ $service_name started successfully"
    else
        echo "❌ Failed to start $service_name"
        echo "Check logs: tail -f $log_file"
    fi
}

# Start all services
echo "🔄 Starting main bot..."
start_service "bot" "bot.py"

echo "💳 Starting payment monitor..."
start_service "payment_monitor" "payment_monitor.py"

echo "📅 Starting ad scheduler..."
start_service "scheduler" "scheduler.py"

echo "🔧 Starting maintenance service..."
start_service "maintenance" "maintenance.py"

# Wait a moment for all services to start
sleep 5

# Check status of all services
echo ""
echo "📊 Service Status:"
echo "=================="

services=("bot.py" "payment_monitor.py" "scheduler.py" "maintenance.py")
for service in "${services[@]}"; do
    if check_process "$service"; then
        echo "✅ $service is running"
    else
        echo "❌ $service is not running"
    fi
done

echo ""
echo "🎉 All services started!"
echo ""
echo "📝 Useful commands:"
echo "  - View bot logs: tail -f bot_output.log"
echo "  - View all logs: tail -f logs/*.log"
echo "  - Stop all services: pkill -f 'python.*\.py'"
echo "  - Restart services: ./start_all_services.sh"
echo ""
echo "🤖 Your bot is now ready to use!"
echo "   Find it on Telegram and send /start to test" 