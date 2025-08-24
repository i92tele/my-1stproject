#!/usr/bin/env python3
"""
Fix Bot Responsiveness

This script diagnoses and fixes issues with the bot not responding to UI interactions.
It checks:
1. Telegram API connection
2. Message handler registration
3. Webhook vs polling configuration
4. Bot token validity

Usage:
    python fix_bot_responsiveness.py
"""

import logging
import os
import sys
import json
import sqlite3
import signal
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

def check_bot_processes():
    """Check if bot processes are running."""
    logger.info("🔍 Checking bot processes...")
    
    try:
        import psutil
        
        bot_processes = []
        scheduler_processes = []
        payment_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if not cmdline:
                    continue
                    
                cmdline_str = ' '.join(cmdline)
                
                if 'python' in cmdline_str and 'bot.py' in cmdline_str:
                    bot_processes.append(proc)
                elif 'python' in cmdline_str and ('scheduler.py' in cmdline_str or '-m scheduler' in cmdline_str):
                    scheduler_processes.append(proc)
                elif 'python' in cmdline_str and 'payment_monitor.py' in cmdline_str:
                    payment_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        logger.info(f"Found {len(bot_processes)} bot processes")
        logger.info(f"Found {len(scheduler_processes)} scheduler processes")
        logger.info(f"Found {len(payment_processes)} payment monitor processes")
        
        return bot_processes, scheduler_processes, payment_processes
        
    except ImportError:
        logger.warning("⚠️ psutil not available, cannot check processes")
        return [], [], []

def check_telegram_api_connection():
    """Check Telegram API connection."""
    logger.info("🔍 Checking Telegram API connection...")
    
    try:
        import requests
        
        # Try to connect to Telegram API
        response = requests.get("https://api.telegram.org", timeout=5)
        if response.status_code == 200:
            logger.info("✅ Telegram API is reachable")
            return True
        else:
            logger.warning(f"⚠️ Telegram API returned status code {response.status_code}")
            return False
            
    except ImportError:
        logger.warning("⚠️ requests not available, cannot check Telegram API connection")
        return False
    except Exception as e:
        logger.error(f"❌ Error checking Telegram API connection: {e}")
        return False

def check_bot_token():
    """Check if bot token is valid."""
    logger.info("🔍 Checking bot token...")
    
    try:
        # Try to find bot token in environment
        import os
        bot_token = os.environ.get("BOT_TOKEN")
        
        if not bot_token:
            # Try to find bot token in .env file
            if os.path.exists(".env"):
                with open(".env", "r") as f:
                    for line in f:
                        if line.startswith("BOT_TOKEN="):
                            bot_token = line.strip().split("=", 1)[1].strip()
                            break
        
        if not bot_token:
            logger.warning("⚠️ Could not find BOT_TOKEN in environment or .env file")
            return False
        
        # Check if token has correct format
        parts = bot_token.split(":")
        if len(parts) != 2 or not parts[0].isdigit() or len(parts[1]) < 30:
            logger.warning("⚠️ Bot token has invalid format")
            return False
        
        logger.info("✅ Bot token format is valid")
        
        # Try to connect to Telegram API with token
        import requests
        response = requests.get(f"https://api.telegram.org/bot{bot_token}/getMe", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                bot_username = data.get("result", {}).get("username")
                logger.info(f"✅ Bot token is valid (username: @{bot_username})")
                return True
            else:
                logger.warning(f"⚠️ Bot token validation failed: {data.get('description')}")
                return False
        else:
            logger.warning(f"⚠️ Bot token validation failed with status code {response.status_code}")
            return False
            
    except ImportError:
        logger.warning("⚠️ requests not available, cannot check bot token")
        return False
    except Exception as e:
        logger.error(f"❌ Error checking bot token: {e}")
        return False

def fix_bot_configuration():
    """Fix bot configuration issues."""
    logger.info("🔧 Fixing bot configuration...")
    
    try:
        # Check if bot.py exists
        if not os.path.exists("bot.py"):
            logger.error("❌ bot.py does not exist")
            return False
        
        with open("bot.py", "r") as f:
            content = f.read()
        
        # Check if bot is using polling instead of webhook
        if "start_polling" not in content and "start_webhook" not in content:
            logger.warning("⚠️ Could not determine if bot is using polling or webhook")
            return False
        
        using_webhook = "start_webhook" in content
        logger.info(f"Bot is using {'webhook' if using_webhook else 'polling'}")
        
        if using_webhook:
            # Recommend switching to polling for better reliability
            logger.info("ℹ️ For better reliability during testing, consider switching from webhook to polling")
            
        # Check if error handlers are registered
        has_error_handler = "add_error_handler" in content
        if not has_error_handler:
            logger.warning("⚠️ No error handler found in bot.py")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error fixing bot configuration: {e}")
        return False

def restart_bot():
    """Restart the bot processes."""
    logger.info("🔄 Restarting bot processes...")
    
    try:
        # Check if start_bot.py exists
        if os.path.exists("start_bot.py"):
            logger.info("Found start_bot.py, using it to restart the bot")
            
            # Kill existing processes
            bot_processes, scheduler_processes, payment_processes = check_bot_processes()
            
            for proc in bot_processes + scheduler_processes + payment_processes:
                try:
                    proc.terminate()
                    logger.info(f"Terminated process {proc.info['pid']}")
                except Exception as e:
                    logger.error(f"Error terminating process {proc.info['pid']}: {e}")
            
            # Wait for processes to terminate
            time.sleep(2)
            
            # Start the bot
            logger.info("Starting the bot...")
            os.system("python start_bot.py &")
            
            logger.info("✅ Bot restarted")
            return True
        else:
            logger.warning("⚠️ start_bot.py not found, cannot restart bot automatically")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error restarting bot: {e}")
        return False

def main():
    """Main function."""
    logger.info("=" * 60)
    logger.info("🚀 DIAGNOSING BOT RESPONSIVENESS ISSUES")
    logger.info("=" * 60)
    
    # Check bot processes
    bot_processes, scheduler_processes, payment_processes = check_bot_processes()
    
    # Check Telegram API connection
    api_reachable = check_telegram_api_connection()
    
    # Check bot token
    token_valid = check_bot_token()
    
    # Fix bot configuration
    fix_bot_configuration()
    
    # Summary
    logger.info("=" * 60)
    logger.info("📊 DIAGNOSIS SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Bot processes: {'✅ Running' if bot_processes else '❌ Not running'}")
    logger.info(f"Scheduler processes: {'✅ Running' if scheduler_processes else '❌ Not running'}")
    logger.info(f"Payment monitor processes: {'✅ Running' if payment_processes else '❌ Not running'}")
    logger.info(f"Telegram API: {'✅ Reachable' if api_reachable else '❌ Not reachable'}")
    logger.info(f"Bot token: {'✅ Valid' if token_valid else '❌ Invalid or not found'}")
    
    # Recommendations
    logger.info("=" * 60)
    logger.info("💡 RECOMMENDATIONS")
    logger.info("=" * 60)
    
    if not bot_processes:
        logger.info("▶️ Start the bot using: python start_bot.py")
    elif not api_reachable:
        logger.info("🔄 Check your internet connection and try again")
    elif not token_valid:
        logger.info("🔑 Check your BOT_TOKEN in the .env file")
    else:
        logger.info("🔄 Restart the bot to refresh the connection")
        
    logger.info("=" * 60)
    logger.info("Would you like to restart the bot now? (y/n)")
    
    try:
        choice = input().strip().lower()
        if choice == 'y':
            restart_bot()
        else:
            logger.info("Restart cancelled")
    except:
        logger.info("No input received, skipping restart")

if __name__ == "__main__":
    main()
