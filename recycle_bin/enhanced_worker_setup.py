#!/usr/bin/env python3
"""
Enhanced Unified Worker Setup Script
Streamlined setup with better credential management and validation
"""

import os
import asyncio
import sqlite3
import time
import json
import webbrowser
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, ApiIdInvalidError, PhoneNumberInvalidError
import logging
from typing import Dict, List, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedWorkerSetup:
    def __init__(self, db_path: str = 'bot_database.db'):
        self.db_path = db_path
        self.workers = []
        self.sessions_dir = "sessions"
        self.credentials_file = "worker_credentials.json"
        
    async def initialize_database(self):
        """Initialize database tables for worker management."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create workers table for persistent storage
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS workers (
                    worker_id INTEGER PRIMARY KEY,
                    api_id TEXT NOT NULL,
                    api_hash TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    is_registered BOOLEAN DEFAULT 0,
                    registration_date TEXT,
                    last_used TEXT,
                    session_file TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create worker_usage table for tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS worker_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER,
                    hourly_posts INTEGER DEFAULT 0,
                    daily_posts INTEGER DEFAULT 0,
                    hourly_limit INTEGER DEFAULT 15,
                    daily_limit INTEGER DEFAULT 100,
                    last_reset TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (worker_id) REFERENCES workers (worker_id)
                )
            ''')
            
            # Create worker_health table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS worker_health (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER,
                    status TEXT DEFAULT 'healthy',
                    last_check TEXT,
                    error_count INTEGER DEFAULT 0,
                    ban_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (worker_id) REFERENCES workers (worker_id)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ Database tables initialized for worker management")
            
        except Exception as e:
            logger.error(f"❌ Error initializing database: {e}")
    
    def load_existing_credentials(self) -> Dict:
        """Load existing credentials from file."""
        if os.path.exists(self.credentials_file):
            try:
                with open(self.credentials_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load existing credentials: {e}")
        return {}
    
    def save_credentials(self, credentials: Dict):
        """Save credentials to file for future use."""
        try:
            with open(self.credentials_file, 'w') as f:
                json.dump(credentials, f, indent=2)
            logger.info("✅ Credentials saved to file")
        except Exception as e:
            logger.error(f"❌ Error saving credentials: {e}")
    
    def collect_phone_numbers(self) -> bool:
        """Collect phone numbers from user input."""
        print("📱 ENHANCED WORKER SETUP")
        print("=" * 60)
        print("This script will help you set up Telegram workers efficiently!")
        print("")
        print("📋 STEP 1: Enter phone numbers")
        print("Enter phone numbers (one per line, empty line to finish):")
        print("Example: +1234567890")
        print("")
        
        worker_id = 1
        while True:
            phone = input(f"Worker {worker_id} phone number: ").strip()
            if not phone:
                break
                
            # Validate and format phone number
            if not phone.startswith('+'):
                phone = '+' + phone.replace(' ', '').replace('-', '')
            
            # Basic validation
            if len(phone) < 8:
                print("❌ Phone number too short. Please try again.")
                continue
                
            self.workers.append({
                'worker_id': worker_id,
                'phone': phone,
                'status': 'pending'
            })
            
            print(f"✅ Added Worker {worker_id}: {phone}")
            worker_id += 1
        
        print(f"\n📊 Total workers to set up: {len(self.workers)}")
        return len(self.workers) > 0
    
    def get_api_credentials_interactive(self, worker: Dict) -> Optional[Dict]:
        """Interactive API credential collection with guidance."""
        print(f"\n🔑 STEP 2: API Credentials for Worker {worker['worker_id']}")
        print("=" * 60)
        print(f"📞 Phone: {worker['phone']}")
        print("")
        
        # Check if we have existing credentials
        existing_creds = self.load_existing_credentials()
        if worker['phone'] in existing_creds:
            print(f"✅ Found existing credentials for {worker['phone']}")
            use_existing = input("Use existing credentials? (y/n): ").strip().lower()
            if use_existing == 'y':
                return existing_creds[worker['phone']]
        
        print("📋 TO GET API CREDENTIALS:")
        print("   1. I'll open https://my.telegram.org in your browser")
        print(f"   2. Log in with phone: {worker['phone']}")
        print("   3. Go to 'API development tools'")
        print("   4. Create new application with these details:")
        print(f"      - App title: WorkerBot{worker['worker_id']}")
        print(f"      - Short name: wbot{worker['worker_id']}")
        print("      - Platform: Desktop")
        print("      - Description: Telegram Worker Bot")
        print("   5. Copy API ID and API Hash")
        print("")
        
        # Offer to open browser
        open_browser = input("Open browser automatically? (y/n): ").strip().lower()
        if open_browser == 'y':
            try:
                webbrowser.open('https://my.telegram.org')
                print("🌐 Browser opened. Please complete the steps above.")
            except:
                print("❌ Could not open browser. Please go to https://my.telegram.org manually")
        
        print("\n" + "="*60)
        print("ENTER YOUR API CREDENTIALS:")
        
        while True:
            api_id = input(f"API ID for {worker['phone']}: ").strip()
            api_hash = input(f"API Hash for {worker['phone']}: ").strip()
            
            if not api_id or not api_hash:
                print("❌ Both API ID and API Hash are required!")
                continue
            
            # Basic validation
            try:
                int(api_id)
            except ValueError:
                print("❌ API ID should be a number!")
                continue
                
            if len(api_hash) < 32:
                print("❌ API Hash seems too short. Please check and try again.")
                continue
            
            credentials = {
                'api_id': api_id,
                'api_hash': api_hash
            }
            
            # Save credentials for future use
            existing_creds[worker['phone']] = credentials
            self.save_credentials(existing_creds)
            
            return credentials
    
    async def setup_worker_with_verification(self, worker: Dict) -> bool:
        """Set up worker with SMS verification only."""
        try:
            print(f"\n�� STEP 3: Setting up Worker {worker['worker_id']}")
            print("=" * 60)
            print(f"📞 Phone: {worker['phone']}")
            
            # Get API credentials
            credentials = self.get_api_credentials_interactive(worker)
            if not credentials:
                print(f"❌ Failed to get credentials for {worker['phone']}")
                return False
            
            worker['api_id'] = credentials['api_id']
            worker['api_hash'] = credentials['api_hash']
            
            # Ensure sessions directory exists
            os.makedirs(self.sessions_dir, exist_ok=True)
            
            # Create session file path
            session_file = f"{self.sessions_dir}/worker_{worker['worker_id']}.session"
            worker['session_file'] = session_file
            
            print(f"📡 Connecting to Telegram...")
            
            # Create Telethon client with better error handling
            try:
                client = TelegramClient(session_file, worker['api_id'], worker['api_hash'])
                await client.connect()
            except ApiIdInvalidError:
                print(f"❌ Invalid API credentials for {worker['phone']}")
                print("Please check your API ID and API Hash and try again.")
                return False
            except Exception as e:
                print(f"❌ Connection error: {e}")
                return False
            
            # Check if already authorized
            if await client.is_user_authorized():
                print(f"✅ Worker {worker['worker_id']} already authorized!")
                me = await client.get_me()
                worker['username'] = me.username or f"worker_{worker['worker_id']}"
                worker['first_name'] = me.first_name or ""
                worker['last_name'] = me.last_name or ""
                worker['status'] = 'authorized'
                await client.disconnect()
                return True
            
            # Send verification code
            print(f"📤 Sending verification code to {worker['phone']}...")
            try:
                await client.send_code_request(worker['phone'])
                print(f"✅ Verification code sent!")
            except PhoneNumberInvalidError:
                print(f"❌ Invalid phone number: {worker['phone']}")
                await client.disconnect()
                return False
            except Exception as e:
                print(f"❌ Error sending code: {e}")
                await client.disconnect()
                return False
            
            # Get verification code from user
            print(f"\n📱 CHECK YOUR PHONE: {worker['phone']}")
            print("You should receive a verification code via SMS.")
            
            max_attempts = 3
            for attempt in range(max_attempts):
                code = input(f"Enter verification code (attempt {attempt + 1}/{max_attempts}): ").strip()
                
                if not code:
                    print("❌ Please enter the verification code.")
                    continue
                
                try:
                    # Sign in with code
                    await client.sign_in(worker['phone'], code)
                    print(f"✅ Worker {worker['worker_id']} signed in successfully!")
                    break
                    
                except SessionPasswordNeededError:
                    # 2FA password required
                    print(f"🔐 Two-factor authentication enabled for {worker['phone']}")
                    max_password_attempts = 3
                    
                    for pwd_attempt in range(max_password_attempts):
                        password = input(f"Enter 2FA password (attempt {pwd_attempt + 1}/{max_password_attempts}): ").strip()
                        try:
                            await client.sign_in(password=password)
                            print(f"✅ Worker {worker['worker_id']} signed in with 2FA!")
                            break
                        except Exception as pwd_error:
                            print(f"❌ Invalid 2FA password: {pwd_error}")
                            if pwd_attempt == max_password_attempts - 1:
                                print("❌ Max 2FA attempts exceeded")
                                await client.disconnect()
                                return False
                    break
                    
                except PhoneCodeInvalidError:
                    print(f"❌ Invalid verification code")
                    if attempt == max_attempts - 1:
                        print("❌ Max code attempts exceeded")
                        await client.disconnect()
                        return False
                except Exception as e:
                    print(f"❌ Sign-in error: {e}")
                    if attempt == max_attempts - 1:
                        await client.disconnect()
                        return False
            else:
                # All attempts failed
                await client.disconnect()
                return False
            
            # Get user info
            try:
                me = await client.get_me()
                worker['username'] = me.username or f"worker_{worker['worker_id']}"
                worker['first_name'] = me.first_name or ""
                worker['last_name'] = me.last_name or ""
                worker['status'] = 'authorized'
                
                print(f"✅ Worker {worker['worker_id']} setup complete!")
                print(f"   Name: {worker['first_name']} {worker['last_name']}")
                print(f"   Username: @{worker['username']}")
                
            except Exception as e:
                print(f"❌ Error getting user info: {e}")
                worker['status'] = 'authorized'  # Still mark as authorized
            
            await client.disconnect()
            return True
            
        except Exception as e:
            print(f"❌ Unexpected error setting up Worker {worker['worker_id']}: {e}")
            worker['status'] = 'failed'
            return False
    
    async def save_worker_to_database(self, worker: Dict) -> bool:
        """Save worker to database for persistence."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            current_time = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT OR REPLACE INTO workers 
                (worker_id, api_id, api_hash, phone, session_file, username, 
                 first_name, last_name, is_registered, registration_date, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            ''', (worker['worker_id'], worker['api_id'], worker['api_hash'], 
                 worker['phone'], worker['session_file'], worker.get('username'),
                 worker.get('first_name'), worker.get('last_name'), 
                 current_time, current_time))
            
            # Initialize usage and health tracking
            cursor.execute('INSERT OR IGNORE INTO worker_usage (worker_id, last_reset) VALUES (?, ?)', 
                         (worker['worker_id'], current_time))
            cursor.execute('INSERT OR IGNORE INTO worker_health (worker_id, last_check) VALUES (?, ?)', 
                         (worker['worker_id'], current_time))
            
            conn.commit()
            conn.close()
            logger.info(f"✅ Worker {worker['worker_id']} saved to database")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving worker to database: {e}")
            return False
    
    async def setup_all_workers(self):
        """Set up all workers with enhanced error handling."""
        if not self.workers:
            print("❌ No workers to set up")
            return
        
        print(f"\n🚀 SETTING UP {len(self.workers)} WORKERS")
        print("=" * 60)
        
        successful = 0
        failed = 0
        
        for i, worker in enumerate(self.workers, 1):
            print(f"\n{'='*60}")
            print(f"WORKER {i}/{len(self.workers)}")
            print(f"{'='*60}")
            
            if await self.setup_worker_with_verification(worker):
                if await self.save_worker_to_database(worker):
                    successful += 1
                    print(f"💾 Worker {worker['worker_id']} saved to database")
                else:
                    failed += 1
                    print(f"❌ Failed to save worker {worker['worker_id']} to database")
            else:
                failed += 1
            
            # Delay between workers
            if i < len(self.workers):
                print("\n⏳ Waiting 3 seconds before next worker...")
                await asyncio.sleep(3)
        
        print(f"\n�� SETUP COMPLETE!")
        print(f"=" * 30)
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Total: {len(self.workers)}")
    
    def generate_detailed_summary(self):
        """Generate comprehensive setup summary."""
        print(f"\n📋 DETAILED SETUP SUMMARY")
        print("=" * 60)
        
        authorized = [w for w in self.workers if w['status'] == 'authorized']
        failed = [w for w in self.workers if w['status'] == 'failed']
        
        print(f"📊 STATISTICS:")
        print(f"   Total Workers: {len(self.workers)}")
        print(f"   ✅ Authorized: {len(authorized)}")
        print(f"   ❌ Failed: {len(failed)}")
        print(f"   📈 Success Rate: {(len(authorized)/len(self.workers)*100):.1f}%")
        
        if authorized:
            print(f"\n✅ AUTHORIZED WORKERS:")
            print("-" * 40)
            for worker in authorized:
                print(f"   🤖 Worker {worker['worker_id']}:")
                print(f"      📞 Phone: {worker['phone']}")
                print(f"      �� Username: @{worker.get('username', 'N/A')}")
                print(f"      📛 Name: {worker.get('first_name', '')} {worker.get('last_name', '')}")
                print(f"      🔑 API ID: {worker['api_id']}")
                print()
        
        if failed:
            print(f"\n❌ FAILED WORKERS:")
            print("-" * 40)
            for worker in failed:
                print(f"   🤖 Worker {worker['worker_id']}: {worker['phone']}")
        
        print(f"\n📁 FILES CREATED:")
        print(f"   �� Database: {self.db_path}")
        print(f"   📂 Sessions: {self.sessions_dir}/")
        print(f"   �� Credentials: {self.credentials_file}")
        
        print(f"\n🚀 NEXT STEPS:")
        print(f"   1. 🧪 Test workers: python3 test_worker_system.py")
        print(f"   2. 📊 Monitor health: python3 worker_health_monitor.py")
        print(f"   3. 🕐 Start scheduler: python3 -m scheduler")
        print(f"   4. 📈 Check status: python3 worker_status.py")
        
        print(f"\n��️ SECURITY FEATURES:")
        print(f"   ✅ Individual API credentials per worker")
        print(f"   ✅ Secure session management")
        print(f"   ✅ Persistent database storage")
        print(f"   ✅ Credential backup and reuse")
        print(f"   ✅ Enhanced error handling")
        
        if len(authorized) > 0:
            print(f"\n🎉 SETUP SUCCESSFUL!")
            print(f"You now have {len(authorized)} working Telegram workers ready to use!")
        else:
            print(f"\n⚠️ NO WORKERS AUTHORIZED")
            print(f"Please check the error messages above and try again.")

async def main():
    """Main function with enhanced user experience."""
    print("�� ENHANCED TELEGRAM WORKER SETUP")
    print("=" * 60)
    print("Welcome to the streamlined worker setup process!")
    print("This script will guide you through setting up multiple Telegram workers.")
    print("")
    print("📋 REQUIREMENTS:")
    print("   ✅ Phone numbers with SMS access")
    print("   ✅ Internet connection")
    print("   ✅ Telegram account for each phone")
    print("")
    
    input("Press Enter to continue...")
    
    setup = EnhancedWorkerSetup()
    
    try:
        # Initialize database
        await setup.initialize_database()
        
        # Collect phone numbers
        if not setup.collect_phone_numbers():
            print("❌ No phone numbers provided. Exiting...")
            return
        
        # Confirm before proceeding
        print(f"\n📋 You're about to set up {len(setup.workers)} workers.")
        print("Each worker will need:")
        print("   - API credentials from my.telegram.org")
        print("   - SMS verification code")
        print("   - 2FA password (if enabled)")
        print("")
        
        confirm = input("Continue with setup? (y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ Setup cancelled by user")
            return
        
        # Set up all workers
        await setup.setup_all_workers()
        
        # Show detailed summary
        setup.generate_detailed_summary()
        
    except KeyboardInterrupt:
        print("\n\n❌ Setup interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        logger.error(f"Main function error: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
