#!/usr/bin/env python3
"""
Comprehensive Status Report
Checks all important aspects of the bot system
"""

import os
import sys
from dotenv import load_dotenv

def check_env_file():
    """Check .env file configuration."""
    print("🔧 Environment Configuration:")
    print("=" * 40)
    
    load_dotenv('config/.env')
    
    # Check bot configuration
    bot_token = os.getenv('BOT_TOKEN')
    admin_id = os.getenv('ADMIN_ID')
    
    print(f"🤖 Bot Token: {'✅ Set' if bot_token and bot_token != 'your_telegram_bot_token_here' else '❌ Missing/Placeholder'}")
    print(f"👤 Admin ID: {'✅ Set' if admin_id and admin_id != 'your_admin_user_id_here' else '❌ Missing/Placeholder'}")
    
    # Check database
    db_url = os.getenv('DATABASE_URL')
    print(f"🗄️ Database URL: {'✅ Set' if db_url else '❌ Missing'}")
    
    # Check crypto addresses
    ton_address = os.getenv('TON_ADDRESS')
    print(f"💰 TON Address: {'✅ Set' if ton_address and ton_address != 'your_ton_wallet_address_here' else '❌ Missing/Placeholder'}")
    
    # Check workers
    worker_count = 0
    for i in range(1, 20):
        api_id = os.getenv(f'WORKER_{i}_API_ID')
        if api_id:
            worker_count += 1
    
    print(f"👥 Workers Configured: {worker_count}")
    
    return {
        'bot_token': bool(bot_token and bot_token != 'your_telegram_bot_token_here'),
        'admin_id': bool(admin_id and admin_id != 'your_admin_user_id_here'),
        'database': bool(db_url),
        'ton_address': bool(ton_address and ton_address != 'your_ton_wallet_address_here'),
        'workers': worker_count
    }

def check_files():
    """Check important files."""
    print("\n📁 Important Files:")
    print("=" * 40)
    
    important_files = [
        'bot.py',
        'scheduler.py',
        'database.py',
        'ton_payments.py',
        'config.py',
        'commands/user_commands.py',
        'commands/admin_commands.py',
        'enhanced_ui.py'
    ]
    
    missing_files = []
    for file in important_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file}")
            missing_files.append(file)
    
    return len(missing_files) == 0

def check_session_files():
    """Check worker session files."""
    print("\n📱 Worker Sessions:")
    print("=" * 40)
    
    session_files = [f for f in os.listdir('.') if f.startswith('session_worker_') and f.endswith('.session')]
    
    if session_files:
        print(f"✅ Found {len(session_files)} session files:")
        for session in sorted(session_files):
            size = os.path.getsize(session)
            print(f"  📄 {session} ({size} bytes)")
    else:
        print("❌ No session files found")
    
    return len(session_files)

def check_git_status():
    """Check git status."""
    print("\n📦 Git Status:")
    print("=" * 40)
    
    import subprocess
    try:
        result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
        if result.stdout.strip():
            print("⚠️ There are uncommitted changes:")
            for line in result.stdout.strip().split('\n'):
                if line:
                    print(f"  {line}")
        else:
            print("✅ Working directory is clean")
        return True
    except Exception as e:
        print(f"❌ Git check failed: {e}")
        return False

def check_processes():
    """Check running processes."""
    print("\n🔄 Running Processes:")
    print("=" * 40)
    
    import subprocess
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        bot_processes = [line for line in result.stdout.split('\n') if 'python3' in line and ('bot.py' in line or 'scheduler.py' in line)]
        
        if bot_processes:
            print("🟢 Bot processes running:")
            for process in bot_processes:
                print(f"  {process}")
        else:
            print("🔴 No bot processes running")
        
        return len(bot_processes)
    except Exception as e:
        print(f"❌ Process check failed: {e}")
        return 0

def check_database():
    """Check database connection."""
    print("\n🗄️ Database Status:")
    print("=" * 40)
    
    try:
        import asyncpg
        import asyncio
        
        async def test_db():
            load_dotenv('config/.env')
            db_url = os.getenv('DATABASE_URL')
            if not db_url:
                print("❌ No database URL configured")
                return False
            
            try:
                conn = await asyncpg.connect(db_url)
                await conn.close()
                print("✅ Database connection successful")
                return True
            except Exception as e:
                print(f"❌ Database connection failed: {e}")
                return False
        
        return asyncio.run(test_db())
    except ImportError:
        print("❌ asyncpg not installed")
        return False
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False

def main():
    """Run comprehensive status check."""
    print("🚀 AutoFarming Pro - Status Report")
    print("=" * 50)
    
    # Run all checks
    env_status = check_env_file()
    files_ok = check_files()
    session_count = check_session_files()
    git_ok = check_git_status()
    process_count = check_processes()
    db_ok = check_database()
    
    # Summary
    print("\n📊 Summary:")
    print("=" * 40)
    
    issues = []
    if not env_status['bot_token']:
        issues.append("Bot token not configured")
    if not env_status['admin_id']:
        issues.append("Admin ID not configured")
    if not env_status['database']:
        issues.append("Database URL not configured")
    if not env_status['ton_address']:
        issues.append("TON address not configured")
    if env_status['workers'] < 5:
        issues.append(f"Only {env_status['workers']} workers configured (need at least 5)")
    if not files_ok:
        issues.append("Missing important files")
    if session_count < 5:
        issues.append(f"Only {session_count} session files found")
    if process_count == 0:
        issues.append("No bot processes running")
    if not db_ok:
        issues.append("Database connection failed")
    
    if issues:
        print("⚠️ Issues found:")
        for issue in issues:
            print(f"  • {issue}")
    else:
        print("✅ All systems operational!")
    
    print(f"\n📈 Stats:")
    print(f"  • Workers configured: {env_status['workers']}")
    print(f"  • Session files: {session_count}")
    print(f"  • Running processes: {process_count}")

if __name__ == "__main__":
    main() 