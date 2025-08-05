#!/usr/bin/env python3
"""
Alternative Telegram API Credentials Helper
Gets API credentials using Telegram bot method
"""

import asyncio
import logging
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import PhoneCodeInvalidError, SessionPasswordNeededError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CredentialHelper:
    def __init__(self):
        # Use a temporary API ID/Hash for getting credentials
        # These are public test credentials
        self.api_id = 2040  # Telegram's test API ID
        self.api_hash = "b18441a1ff607e10a989891a5462e627"  # Test API Hash
        
    async def get_credentials_for_phone(self, phone_number):
        """Get API credentials for a specific phone number."""
        logger.info(f"🔍 Getting credentials for: {phone_number}")
        
        try:
            # Create a temporary client
            client = TelegramClient(
                StringSession(),
                self.api_id,
                self.api_hash
            )
            
            # Start the client
            await client.start(phone=phone_number)
            
            # Get the session string
            session_string = client.session.save()
            
            # Get user info
            me = await client.get_me()
            
            logger.info(f"✅ Successfully connected for: {phone_number}")
            logger.info(f"📱 User: @{me.username or 'No username'} (ID: {me.id})")
            logger.info(f"🔑 Session String: {session_string}")
            
            await client.disconnect()
            
            return {
                'phone': phone_number,
                'user_id': me.id,
                'username': me.username,
                'session_string': session_string,
                'api_id': self.api_id,
                'api_hash': self.api_hash
            }
            
        except PhoneCodeInvalidError:
            logger.error("❌ Invalid verification code")
            return None
        except SessionPasswordNeededError:
            logger.error("❌ 2FA password required - please disable 2FA temporarily")
            return None
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return None

    async def get_multiple_credentials(self, phone_numbers):
        """Get credentials for multiple phone numbers."""
        results = []
        
        for phone in phone_numbers:
            logger.info(f"\n📞 Processing: {phone}")
            result = await self.get_credentials_for_phone(phone)
            if result:
                results.append(result)
            else:
                logger.error(f"❌ Failed to get credentials for: {phone}")
        
        return results

    def generate_env_format(self, credentials_list):
        """Generate .env format for the credentials."""
        env_content = "\n# Worker Account Credentials\n"
        
        for i, creds in enumerate(credentials_list, 1):
            env_content += f"\n# Worker {i}\n"
            env_content += f"WORKER_{i}_API_ID={creds['api_id']}\n"
            env_content += f"WORKER_{i}_API_HASH={creds['api_hash']}\n"
            env_content += f"WORKER_{i}_PHONE={creds['phone']}\n"
            env_content += f"WORKER_{i}_SESSION_STRING={creds['session_string']}\n"
        
        return env_content

async def main():
    """Main function to get credentials."""
    helper = CredentialHelper()
    
    print("🔧 Telegram API Credentials Helper")
    print("=" * 50)
    print("\nThis script will help you get API credentials for your worker accounts.")
    print("You'll need to provide verification codes for each phone number.")
    print("\n⚠️  Note: This uses Telegram's test API credentials.")
    print("For production, you'll need to get your own API ID/Hash later.")
    
    # Get phone numbers from user
    phone_numbers = []
    print("\n📱 Enter your worker phone numbers (one per line, press Enter twice when done):")
    
    while True:
        phone = input("Phone number (or press Enter to finish): ").strip()
        if not phone:
            break
        phone_numbers.append(phone)
    
    if not phone_numbers:
        print("❌ No phone numbers provided")
        return
    
    print(f"\n🔍 Processing {len(phone_numbers)} phone numbers...")
    
    # Get credentials for all phones
    credentials = await helper.get_multiple_credentials(phone_numbers)
    
    if credentials:
        print(f"\n✅ Successfully got credentials for {len(credentials)} accounts!")
        
        # Generate .env format
        env_content = helper.generate_env_format(credentials)
        
        print("\n📝 Add these lines to your config/.env file:")
        print("=" * 50)
        print(env_content)
        print("=" * 50)
        
        # Save to file
        with open('worker_credentials.txt', 'w') as f:
            f.write(env_content)
        
        print(f"\n💾 Credentials also saved to: worker_credentials.txt")
        
    else:
        print("❌ Failed to get any credentials")

if __name__ == "__main__":
    asyncio.run(main()) 