#!/usr/bin/env python3
import os
import sys
import logging
import signal
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/simple_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Received shutdown signal, stopping bot...")
    sys.exit(0)

def main():
    """Start the bot with minimal services."""
    logger.info("Starting Simple Bot (Main Bot Only)...")
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Activate virtual environment
    venv_path = os.path.join(os.path.dirname(__file__), 'venv', 'bin', 'activate_this.py')
    if os.path.exists(venv_path):
        exec(open(venv_path).read(), {'__file__': venv_path})
    
    # Import and run bot
    try:
        from bot import AutoFarmingBot
        logger.info("Bot imported successfully, starting...")
        bot = AutoFarmingBot()
        bot.run()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 