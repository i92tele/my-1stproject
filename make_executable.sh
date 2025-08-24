#!/bin/bash
chmod +x sanitize.sh
chmod +x start_bot_simple.sh
chmod +x start_bot_simple_delayed.sh
chmod +x start_all_services.sh
chmod +x start_services_properly.sh
chmod +x start_services_separate_sessions.sh
chmod +x stop_simple.sh
chmod +x stop_all_services.sh
chmod +x test_bot_startup.py
chmod +x bot_simple.py
chmod +x bot_standalone.py
chmod +x bot_no_polling.py
echo "All scripts are now executable!"
echo "You can run them with:"
echo "  ./sanitize.sh - Clean up processes"
echo "  ./start_bot_simple.sh - Start bot with payment monitor"
echo "  ./start_bot_simple_delayed.sh - Start bot FIRST, scheduler LAST (recommended)"
echo "  ./start_all_services.sh - Start all services (bot, scheduler, payment monitor)"
echo "  ./start_services_properly.sh - Start all services with proper isolation"
echo "  ./start_services_separate_sessions.sh - Start all services in separate screen sessions"
echo "  ./stop_simple.sh - Stop all services (simple)"
echo "  ./stop_all_services.sh - Stop all services (detailed)"
echo "  python3 test_bot_startup.py - Test bot startup"
