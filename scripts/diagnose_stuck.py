#!/usr/bin/env python3
import os
import sys
import psutil
import logging
import asyncio
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BotDiagnostic:
    def __init__(self):
        self.issues = []
        
    def check_processes(self):
        """Check for running bot processes."""
        logger.info("Checking for running bot processes...")
        
        bot_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                if 'bot.py' in cmdline or 'scheduler.py' in cmdline:
                    bot_processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmdline': cmdline,
                        'cpu_percent': proc.cpu_percent(),
                        'memory_percent': proc.memory_percent(),
                        'create_time': datetime.fromtimestamp(proc.create_time())
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
        if bot_processes:
            logger.info(f"Found {len(bot_processes)} bot processes:")
            for proc in bot_processes:
                logger.info(f"  PID {proc['pid']}: {proc['name']} - CPU: {proc['cpu_percent']}%, Memory: {proc['memory_percent']}%")
                logger.info(f"    Started: {proc['create_time']}")
                logger.info(f"    Command: {proc['cmdline']}")
        else:
            logger.info("No bot processes found running")
            
        return bot_processes
        
    def check_files(self):
        """Check for problematic files."""
        logger.info("Checking for problematic files...")
        
        problematic_files = []
        
        # Check lock files
        lock_files = ['bot.lock']
        for file in lock_files:
            if os.path.exists(file):
                mtime = datetime.fromtimestamp(os.path.getmtime(file))
                age = datetime.now() - mtime
                if age > timedelta(minutes=10):
                    problematic_files.append(f"Stale lock file: {file} (age: {age})")
                    
        # Check session files
        session_files = [
            'session_worker_1.session', 'session_worker_2.session',
            'session_worker_3.session', 'session_worker_4.session',
            'session_worker_5.session'
        ]
        
        for file in session_files:
            if os.path.exists(file):
                size = os.path.getsize(file)
                if size < 1000:  # Less than 1KB
                    problematic_files.append(f"Corrupted session file: {file} (size: {size} bytes)")
                    
        # Check log files
        log_files = ['logs/bot.log', 'logs/scheduler.log']
        for file in log_files:
            if os.path.exists(file):
                mtime = datetime.fromtimestamp(os.path.getmtime(file))
                age = datetime.now() - mtime
                if age > timedelta(minutes=5):
                    problematic_files.append(f"Stale log file: {file} (last update: {age} ago)")
                    
        if problematic_files:
            logger.warning("Found problematic files:")
            for file in problematic_files:
                logger.warning(f"  {file}")
        else:
            logger.info("No problematic files found")
            
        return problematic_files
        
    def check_database(self):
        """Check database connectivity."""
        logger.info("Checking database connectivity...")
        
        try:
            # Try to import and test database connection
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from src.database.manager import DatabaseManager
            from config import BotConfig
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config, logger)
            
            # Test connection
            async def test_db():
                try:
                    await db.initialize()
                    async with db.pool.acquire() as conn:
                        result = await conn.fetchval("SELECT 1")
                        if result == 1:
                            logger.info("Database connection successful")
                            return True
                except Exception as e:
                    logger.error(f"Database connection failed: {e}")
                    return False
                finally:
                    await db.close()
                    
            return asyncio.run(test_db())
            
        except Exception as e:
            logger.error(f"Database check failed: {e}")
            return False
            
    def check_telegram_api(self):
        """Check Telegram API connectivity."""
        logger.info("Checking Telegram API connectivity...")
        
        try:
            import requests
            
            # You'll need to get your bot token from config
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from config import BotConfig
            
            config = BotConfig.load_from_env()
            
            response = requests.get(f"https://api.telegram.org/bot{config.bot_token}/getMe", timeout=10)
            
            if response.status_code == 200:
                logger.info("Telegram API connection successful")
                return True
            else:
                logger.error(f"Telegram API connection failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Telegram API check failed: {e}")
            return False
            
    def check_system_resources(self):
        """Check system resources."""
        logger.info("Checking system resources...")
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        logger.info(f"CPU usage: {cpu_percent}%")
        
        # Memory usage
        memory = psutil.virtual_memory()
        logger.info(f"Memory usage: {memory.percent}%")
        
        # Disk usage
        disk = psutil.disk_usage('.')
        logger.info(f"Disk usage: {disk.percent}%")
        
        # Check for resource issues
        issues = []
        if cpu_percent > 80:
            issues.append(f"High CPU usage: {cpu_percent}%")
        if memory.percent > 80:
            issues.append(f"High memory usage: {memory.percent}%")
        if disk.percent > 90:
            issues.append(f"High disk usage: {disk.percent}%")
            
        if issues:
            logger.warning("System resource issues detected:")
            for issue in issues:
                logger.warning(f"  {issue}")
        else:
            logger.info("System resources are normal")
            
        return issues
        
    def run_diagnosis(self):
        """Run complete diagnosis."""
        logger.info("Starting bot diagnosis...")
        
        # Check processes
        processes = self.check_processes()
        
        # Check files
        files = self.check_files()
        
        # Check database
        db_ok = self.check_database()
        
        # Check Telegram API
        api_ok = self.check_telegram_api()
        
        # Check system resources
        resource_issues = self.check_system_resources()
        
        # Summary
        logger.info("\n" + "="*50)
        logger.info("DIAGNOSIS SUMMARY")
        logger.info("="*50)
        
        if processes:
            logger.info(f"✅ Found {len(processes)} bot processes running")
        else:
            logger.warning("❌ No bot processes found")
            
        if files:
            logger.warning(f"⚠️  Found {len(files)} problematic files")
        else:
            logger.info("✅ No problematic files found")
            
        if db_ok:
            logger.info("✅ Database connection OK")
        else:
            logger.error("❌ Database connection failed")
            
        if api_ok:
            logger.info("✅ Telegram API connection OK")
        else:
            logger.error("❌ Telegram API connection failed")
            
        if resource_issues:
            logger.warning(f"⚠️  Found {len(resource_issues)} system resource issues")
        else:
            logger.info("✅ System resources OK")
            
        # Recommendations
        logger.info("\nRECOMMENDATIONS:")
        
        if not processes:
            logger.info("  - Start the bot using: python3 start_bot_safe.py")
            
        if files:
            logger.info("  - Run cleanup: python3 fix_scheduler_stuck.py")
            
        if not db_ok:
            logger.info("  - Check database configuration in config/.env")
            
        if not api_ok:
            logger.info("  - Check bot token in config/.env")
            
        if resource_issues:
            logger.info("  - Consider restarting the system or freeing up resources")
            
        logger.info("="*50)

def main():
    diagnostic = BotDiagnostic()
    diagnostic.run_diagnosis()

if __name__ == '__main__':
    main() 