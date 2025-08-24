#!/usr/bin/env python3
"""
Fully Automated Worker Setup with Playwright
Automatically generates API credentials and sets up workers
"""

import os
import asyncio
import sqlite3
import json
import random
import string
from datetime import datetime
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, ApiIdInvalidError
import logging
from typing import Dict, List, Optional
try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None
    PlaywrightTimeoutError = Exception

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AutomatedWorkerSetup:
    def __init__(self, db_path: str = 'bot_database.db'):
        self.db_path = db_path
        self.workers = []
        self.sessions_dir = "sessions"
        self.credentials_file = "worker_credentials.json"
        self.playwright = None
        self.browser = None
        
    async def initialize_database(self):
        """Initialize database tables for worker management."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create workers table
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
            
            # Create worker_usage table
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
            logger.info("✅ Database tables initialized")
            
        except Exception as e:
            logger.error(f"❌ Error initializing database: {e}")
    
    async def init_playwright(self):
        """Initialize Playwright browser."""
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("❌ Playwright not available. Install with: pip install playwright && playwright install chromium")
            return False
            
        try:
            self.playwright = await async_playwright().start()
            
            # Launch browser with realistic settings
            self.browser = await self.playwright.chromium.launch(
                headless=False,  # Set to True for production
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ]
            )
            logger.info("✅ Playwright browser initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error initializing Playwright: {e}")
            return False
    
    async def close_playwright(self):
        """Clean up Playwright resources."""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("✅ Playwright resources cleaned up")
        except Exception as e:
            logger.error(f"❌ Error closing Playwright: {e}")
    
    def generate_app_details(self, worker_id: int) -> Dict[str, str]:
        """Generate realistic app details for Telegram API."""
        app_names = [
            "MyTelegramApp", "TelegramHelper", "ChatBot", "MessageBot",
            "TelegramTool", "AutoBot", "SmartBot", "TelegramClient",
            "MessageHelper", "TelegramAssistant", "ChatHelper", "AutoHelper"
        ]
        
        short_names = [
            "mytgapp", "tghelper", "chatbot", "msgbot",
            "tgtool", "autobot", "smartbot", "tgclient",
            "msghelper", "tgassist", "chathelp", "autohelp"
        ]
        
        descriptions = [
            "Telegram automation tool for personal use",
            "Personal messaging assistant",
            "Automated chat management tool",
            "Personal Telegram client application",
            "Message automation helper",
            "Personal communication tool"
        ]
        
        # Generate unique names
        base_name = random.choice(app_names)
        base_short = random.choice(short_names)
        
        return {
            "title": f"{base_name}{worker_id}",
            "short_name": f"{base_short}{worker_id}",
            "description": random.choice(descriptions),
            "url": "https://github.com/",
            "platform": "Desktop"
        }
    
    async def login_to_telegram_org(self, page, phone: str) -> bool:
        """Login to my.telegram.org with phone number."""
        try:
            logger.info(f"🔐 Logging in to my.telegram.org with {phone}")
            
            # Navigate to my.telegram.org
            await page.goto('https://my.telegram.org', wait_until='domcontentloaded')
            await asyncio.sleep(2)
            
            # Enter phone number
            phone_input = await page.wait_for_selector('input[name="phone"]', timeout=10000)
            await phone_input.fill(phone)
            await asyncio.sleep(1)
            
            # Click login button
            login_button = await page.wait_for_selector('button[type="submit"]', timeout=5000)
            await login_button.click()
            
            # Wait for confirmation code input
            print(f"📱 SMS verification code will be sent to {phone}")
            print("⏳ Waiting for code input page to load...")
            
            # Wait for the code input page
            await page.wait_for_selector('input[name="password"]', timeout=30000)
            logger.info("✅ Code input page loaded")
            
            # Get verification code from user
            code = input(f"Enter SMS verification code for {phone}: ").strip()
            
            # Enter verification code
            code_input = await page.wait_for_selector('input[name="password"]', timeout=5000)
            await code_input.fill(code)
            await asyncio.sleep(1)
            
            # Submit code
            submit_button = await page.wait_for_selector('button[type="submit"]', timeout=5000)
            await submit_button.click()
            
            # Check for 2FA
            await asyncio.sleep(3)
            try:
                # Check if 2FA password is required
                twofa_input = await page.wait_for_selector('input[name="password"]', timeout=5000)
                if twofa_input:
                    print("🔐 2FA password required")
                    password = input(f"Enter 2FA password for {phone}: ").strip()
                    await twofa_input.fill(password)
                    
                    submit_2fa = await page.wait_for_selector('button[type="submit"]', timeout=5000)
                    await submit_2fa.click()
                    await asyncio.sleep(3)
            except:
                # No 2FA required
                pass
            
            # Verify login success by checking for main page elements
            try:
                await page.wait_for_selector('h1', timeout=10000)
                current_url = page.url
                if 'my.telegram.org' in current_url and 'auth' not in current_url:
                    logger.info("✅ Successfully logged in to my.telegram.org")
                    return True
            except:
                pass
            
            logger.error("❌ Login failed or redirected unexpectedly")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error during login: {e}")
            return False
    
    async def create_api_application(self, page, app_details: Dict[str, str]) -> Optional[Dict[str, str]]:
        """Create API application and extract credentials."""
        try:
            logger.info("🔧 Creating API application...")
            
            # Navigate to API development tools
            await page.goto('https://my.telegram.org/apps', wait_until='domcontentloaded')
            await asyncio.sleep(3)
            
            # Check if app already exists
            try:
                existing_app = await page.wait_for_selector('.app_edit', timeout=5000)
                if existing_app:
                    logger.info("📱 Found existing app, extracting credentials...")
                    
                    # Click on existing app
                    await existing_app.click()
                    await asyncio.sleep(2)
                    
                    # Extract API ID and Hash
                    api_id_element = await page.wait_for_selector('span.form-control[onclick*="select()"]', timeout=10000)
                    api_id = await api_id_element.inner_text()
                    
                    # Find API Hash (it's usually the second span with onclick)
                    hash_elements = await page.query_selector_all('span.form-control[onclick*="select()"]')
                    if len(hash_elements) >= 2:
                        api_hash = await hash_elements[1].inner_text()
                        
                        logger.info("✅ Extracted existing API credentials")
                        return {
                            'api_id': api_id.strip(),
                            'api_hash': api_hash.strip()
                        }
            except:
                # No existing app, create new one
                pass
            
            # Create new application
            logger.info("📝 Creating new API application...")
            
            # Look for create app button/link
            try:
                create_button = await page.wait_for_selector('a[href*="create"]', timeout=5000)
                await create_button.click()
            except:
                # Try alternative selector
                create_button = await page.wait_for_selector('.btn', timeout=5000)
                await create_button.click()
            
            await asyncio.sleep(2)
            
            # Fill application form
            # App title
            title_input = await page.wait_for_selector('input[name="app_title"]', timeout=10000)
            await title_input.fill(app_details['title'])
            
            # Short name
            short_name_input = await page.wait_for_selector('input[name="app_shortname"]', timeout=5000)
            await short_name_input.fill(app_details['short_name'])
            
            # URL (optional)
            try:
                url_input = await page.wait_for_selector('input[name="app_url"]', timeout=3000)
                await url_input.fill(app_details['url'])
            except:
                pass
            
            # Platform
            try:
                platform_select = await page.wait_for_selector('select[name="app_platform"]', timeout=3000)
                await platform_select.select_option('desktop')
            except:
                pass
            
            # Description
            try:
                desc_textarea = await page.wait_for_selector('textarea[name="app_desc"]', timeout=3000)
                await desc_textarea.fill(app_details['description'])
            except:
                pass
            
            # Submit form
            submit_button = await page.wait_for_selector('button[type="submit"]', timeout=5000)
            await submit_button.click()
            await asyncio.sleep(3)
            
            # Extract API credentials from success page
            logger.info("📊 Extracting API credentials...")
            
            # Wait for credentials to appear
            await page.wait_for_selector('span.form-control', timeout=10000)
            
            # Get API ID (usually first span with onclick)
            api_id_element = await page.wait_for_selector('span.form-control[onclick*="select()"]', timeout=5000)
            api_id = await api_id_element.inner_text()
            
            # Get API Hash (usually second span with onclick)
            hash_elements = await page.query_selector_all('span.form-control[onclick*="select()"]')
            if len(hash_elements) >= 2:
                api_hash = await hash_elements[1].inner_text()
            else:
                # Alternative method to find hash
                hash_element = await page.wait_for_selector('span.form-control:not([onclick*="api_id"])', timeout=5000)
                api_hash = await hash_element.inner_text()
            
            credentials = {
                'api_id': api_id.strip(),
                'api_hash': api_hash.strip()
            }
            
            logger.info("✅ Successfully created API application and extracted credentials")
            return credentials
            
        except Exception as e:
            logger.error(f"❌ Error creating API application: {e}")
            return None
    
    async def generate_api_credentials_automatically(self, worker: Dict) -> Optional[Dict[str, str]]:
        """Automatically generate API credentials using Playwright."""
        try:
            logger.info(f"🤖 Auto-generating API credentials for {worker['phone']}")
            
            # Create new page
            context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            # Generate app details
            app_details = self.generate_app_details(worker['worker_id'])
            
            # Login to my.telegram.org
            if not await self.login_to_telegram_org(page, worker['phone']):
                await context.close()
                return None
            
            # Create API application
            credentials = await self.create_api_application(page, app_details)
            
            await context.close()
            return credentials
            
        except Exception as e:
            logger.error(f"❌ Error in auto-generation: {e}")
            return None
    
    def collect_phone_numbers(self) -> bool:
        """Collect phone numbers from user input."""
        print("🤖 FULLY AUTOMATED WORKER SETUP")
        print("=" * 60)
        print("This script will automatically generate API credentials and set up workers!")
        print("You only need to provide phone numbers and SMS verification codes.")
        print("")
        print("📋 Enter phone numbers (one per line, empty line to finish):")
        print("Example: +1234567890")
        print("")
        
        worker_id = 1
        while True:
            phone = input(f"Worker {worker_id} phone number: ").strip()
            if not phone:
                break
                
            # Format phone number
            if not phone.startswith('+'):
                phone = '+' + phone.replace(' ', '').replace('-', '')
            
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
        """Save credentials to file."""
        try:
            with open(self.credentials_file, 'w') as f:
                json.dump(credentials, f, indent=2)
            logger.info("✅ Credentials saved to file")
        except Exception as e:
            logger.error(f"❌ Error saving credentials: {e}")
    
    async def setup_worker_with_automation(self, worker: Dict) -> bool:
        """Set up worker with full automation."""
        try:
            print(f"\n🔧 Setting up Worker {worker['worker_id']}: {worker['phone']}")
            print("=" * 60)
            
            # Check for existing credentials
            existing_creds = self.load_existing_credentials()
            if worker['phone'] in existing_creds:
                print(f"✅ Using existing credentials for {worker['phone']}")
                credentials = existing_creds[worker['phone']]
            else:
                # Generate new credentials automatically
                print("🤖 Automatically generating API credentials...")
                credentials = await self.generate_api_credentials_automatically(worker)
                
                if not credentials:
                    print(f"❌ Failed to generate API credentials for {worker['phone']}")
                    return False
                
                # Save credentials
                existing_creds[worker['phone']] = credentials
                self.save_credentials(existing_creds)
                print("✅ API credentials generated and saved!")
            
            worker['api_id'] = credentials['api_id']
            worker['api_hash'] = credentials['api_hash']
            
            # Set up Telegram client
            os.makedirs(self.sessions_dir, exist_ok=True)
            session_file = f"{self.sessions_dir}/worker_{worker['worker_id']}.session"
            worker['session_file'] = session_file
            
            print(f"📡 Connecting to Telegram...")
            
            # Create and connect client
            client = TelegramClient(session_file, worker['api_id'], worker['api_hash'])
            await client.connect()
            
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
            await client.send_code_request(worker['phone'])
            print(f"✅ Verification code sent!")
            
            # Get verification code
            print(f"\n📱 CHECK YOUR PHONE: {worker['phone']}")
            code = input(f"Enter SMS verification code: ").strip()
            
            try:
                await client.sign_in(worker['phone'], code)
                print(f"✅ Worker {worker['worker_id']} signed in successfully!")
                
            except SessionPasswordNeededError:
                print(f"🔐 2FA required for {worker['phone']}")
                password = input(f"Enter 2FA password: ").strip()
                await client.sign_in(password=password)
                print(f"✅ Worker {worker['worker_id']} signed in with 2FA!")
                
            except PhoneCodeInvalidError:
                print(f"❌ Invalid verification code")
                await client.disconnect()
                return False
            
            # Get user info
            me = await client.get_me()
            worker['username'] = me.username or f"worker_{worker['worker_id']}"
            worker['first_name'] = me.first_name or ""
            worker['last_name'] = me.last_name or ""
            worker['status'] = 'authorized'
            
            print(f"✅ Worker {worker['worker_id']} setup complete!")
            print(f"   Name: {worker['first_name']} {worker['last_name']}")
            print(f"   Username: @{worker['username']}")
            
            await client.disconnect()
            return True
            
        except Exception as e:
            print(f"❌ Error setting up Worker {worker['worker_id']}: {e}")
            worker['status'] = 'failed'
            return False
    
    async def save_worker_to_database(self, worker: Dict) -> bool:
        """Save worker to database."""
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
        """Set up all workers with full automation."""
        if not self.workers:
            print("❌ No workers to set up")
            return
        
        print(f"\n🚀 SETTING UP {len(self.workers)} WORKERS WITH AUTOMATION")
        print("=" * 60)
        
        successful = 0
        failed = 0
        
        for i, worker in enumerate(self.workers, 1):
            print(f"\n{'='*60}")
            print(f"WORKER {i}/{len(self.workers)}")
            print(f"{'='*60}")
            
            if await self.setup_worker_with_automation(worker):
                if await self.save_worker_to_database(worker):
                    successful += 1
                else:
                    failed += 1
            else:
                failed += 1
            
            # Delay between workers
            if i < len(self.workers):
                print("\n⏳ Waiting 5 seconds before next worker...")
                await asyncio.sleep(5)
        
        print(f"\n📊 AUTOMATION COMPLETE!")
        print(f"=" * 30)
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Total: {len(self.workers)}")
    
    def generate_summary(self):
        """Generate setup summary."""
        authorized = [w for w in self.workers if w['status'] == 'authorized']
        failed = [w for w in self.workers if w['status'] == 'failed']
        
        print(f"\n🎉 FULLY AUTOMATED SETUP COMPLETE!")
        print("=" * 60)
        print(f"📊 RESULTS:")
        print(f"   ✅ Successful: {len(authorized)}")
        print(f"   ❌ Failed: {len(failed)}")
        print(f"   📈 Success Rate: {(len(authorized)/len(self.workers)*100):.1f}%")
        
        if authorized:
            print(f"\n✅ AUTHORIZED WORKERS:")
            for worker in authorized:
                print(f"   🤖 Worker {worker['worker_id']}: {worker['phone']} (@{worker.get('username', 'N/A')})")
        
        print(f"\n🚀 WHAT WAS AUTOMATED:")
        print(f"   ✅ API credential generation")
        print(f"   ✅ Telegram account login")
        print(f"   ✅ Application creation")
        print(f"   ✅ Session management")
        print(f"   ✅ Database storage")
        
        print(f"\n📁 FILES CREATED:")
        print(f"   📊 Database: {self.db_path}")
        print(f"   📂 Sessions: {self.sessions_dir}/")
        print(f"   🔐 Credentials: {self.credentials_file}")

async def main():
    """Main function."""
    print("🤖 FULLY AUTOMATED TELEGRAM WORKER SETUP")
    print("=" * 60)
    print("This script uses Playwright to fully automate the worker setup process!")
    print("")
    print("📋 WHAT YOU NEED:")
    print("   ✅ Phone numbers with SMS access")
    print("   ✅ Telegram accounts for each phone")
    print("   ✅ Internet connection")
    print("")
    print("🤖 WHAT GETS AUTOMATED:")
    print("   ✅ API credential generation")
    print("   ✅ my.telegram.org login")
    print("   ✅ Application creation")
    print("   ✅ Session setup")
    print("")
    
    # Check Playwright installation
    if PLAYWRIGHT_AVAILABLE:
        print("✅ Playwright is installed")
    else:
        print("❌ Playwright not installed!")
        print("Run: pip install playwright && playwright install chromium")
        print("⚠️  Worker setup will continue without browser automation")
        print("")
    
    input("Press Enter to start automated setup...")
    
    setup = AutomatedWorkerSetup()
    
    try:
        # Initialize components
        await setup.initialize_database()
        
        if not await setup.init_playwright():
            print("❌ Failed to initialize Playwright")
            return
        
        # Collect phone numbers
        if not setup.collect_phone_numbers():
            print("❌ No phone numbers provided")
            return
        
        # Confirm automation
        print(f"\n🤖 About to automatically set up {len(setup.workers)} workers")
        print("The browser will open and automation will handle:")
        print("   - Logging into my.telegram.org")
        print("   - Creating API applications")
        print("   - Extracting credentials")
        print("   - Setting up Telegram sessions")
        print("")
        
        confirm = input("Start automated setup? (y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ Setup cancelled")
            return
        
        # Run automated setup
        await setup.setup_all_workers()
        
        # Show results
        setup.generate_summary()
        
    except KeyboardInterrupt:
        print("\n❌ Setup interrupted")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logger.error(f"Main error: {e}", exc_info=True)
    finally:
        await setup.close_playwright()

if __name__ == "__main__":
    asyncio.run(main())