#!/usr/bin/env python3
"""
Enhanced Channel Joiner
Handle complex channel joining with multiple steps, captcha, and special procedures
"""

import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError, UserBannedInChannelError, ChatWriteForbiddenError,
    ChannelPrivateError, InviteHashExpiredError, InviteHashInvalidError,
    InviteRequestSentError, UserPrivacyRestrictedError, UserNotMutualContactError
)
from telethon.tl.functions.messages import GetBotCallbackAnswerRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.types import InputPeerChannel, InputPeerChat
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedChannelJoiner:
    """Enhanced channel joiner with multi-step access handling."""
    
    def __init__(self, worker_client: TelegramClient, worker_id: int):
        self.client = worker_client
        self.worker_id = worker_id
        self.join_attempts = {}  # Track join attempts per channel
        self.captcha_solutions = {}  # Store captcha solutions
        
    async def join_channel_enhanced(self, channel_identifier: str) -> dict:
        """Enhanced channel joining with multiple strategies."""
        print(f"🔗 Worker {self.worker_id}: Attempting to join {channel_identifier}")
        
        result = {
            'success': False,
            'method': None,
            'error': None,
            'requires_captcha': False,
            'requires_verification': False,
            'next_steps': []
        }
        
        try:
            # Strategy 1: Direct join with @ symbol
            if channel_identifier.startswith('@'):
                result = await self._try_direct_join(channel_identifier)
                if result['success']:
                    return result
            
            # Strategy 2: Try with t.me format
            if not result['success']:
                t_me_format = f"https://t.me/{channel_identifier.replace('@', '')}"
                result = await self._try_t_me_join(t_me_format)
                if result['success']:
                    return result
            
            # Strategy 3: Try invite link format
            if not result['success']:
                result = await self._try_invite_link(channel_identifier)
                if result['success']:
                    return result
            
            # Strategy 4: Handle forum channels with topic IDs
            if '/' in channel_identifier and not result['success']:
                result = await self._try_forum_channel_join(channel_identifier)
                if result['success']:
                    return result
            
            # Strategy 5: Handle private channels with special access
            if not result['success']:
                result = await self._try_private_channel_access(channel_identifier)
            
            return result
            
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Error joining {channel_identifier}: {e}")
            result['error'] = str(e)
            return result
    
    async def _try_direct_join(self, channel_identifier: str) -> dict:
        """Try direct channel join."""
        try:
            print(f"  📋 Strategy 1: Direct join {channel_identifier}")
            
            # Get the channel entity
            channel = await self.client.get_entity(channel_identifier)
            
            # Try to join
            await self.client(JoinChannelRequest(channel))
            
            print(f"  ✅ Successfully joined {channel_identifier}")
            return {
                'success': True,
                'method': 'direct_join',
                'error': None
            }
            
        except ChannelPrivateError:
            print(f"  ⚠️ Channel {channel_identifier} is private")
            return {
                'success': False,
                'method': 'direct_join',
                'error': 'Channel is private',
                'requires_verification': True
            }
        except UserPrivacyRestrictedError:
            print(f"  ⚠️ Privacy restricted for {channel_identifier}")
            return {
                'success': False,
                'method': 'direct_join',
                'error': 'Privacy restricted',
                'requires_verification': True
            }
        except Exception as e:
            print(f"  ❌ Direct join failed: {e}")
            return {
                'success': False,
                'method': 'direct_join',
                'error': str(e)
            }
    
    async def _try_t_me_join(self, t_me_link: str) -> dict:
        """Try joining via t.me link."""
        try:
            print(f"  📋 Strategy 2: t.me join {t_me_link}")
            
            # Extract channel username from t.me link
            if '/joinchat/' in t_me_link:
                # Private channel with invite hash
                invite_hash = t_me_link.split('/joinchat/')[-1]
                await self.client(ImportChatInviteRequest(invite_hash))
            else:
                # Public channel
                channel_username = t_me_link.split('t.me/')[-1]
                channel = await self.client.get_entity(f"@{channel_username}")
                await self.client(JoinChannelRequest(channel))
            
            print(f"  ✅ Successfully joined via t.me")
            return {
                'success': True,
                'method': 't_me_join',
                'error': None
            }
            
        except InviteHashExpiredError:
            print(f"  ❌ Invite link expired")
            return {
                'success': False,
                'method': 't_me_join',
                'error': 'Invite link expired'
            }
        except InviteHashInvalidError:
            print(f"  ❌ Invalid invite link")
            return {
                'success': False,
                'method': 't_me_join',
                'error': 'Invalid invite link'
            }
        except Exception as e:
            print(f"  ❌ t.me join failed: {e}")
            return {
                'success': False,
                'method': 't_me_join',
                'error': str(e)
            }
    
    async def _try_invite_link(self, channel_identifier: str) -> dict:
        """Try joining via invite link."""
        try:
            print(f"  📋 Strategy 3: Invite link join")
            
            # Check if it's an invite link
            if 't.me/joinchat/' in channel_identifier or 'telegram.me/joinchat/' in channel_identifier:
                invite_hash = channel_identifier.split('/joinchat/')[-1]
                await self.client(ImportChatInviteRequest(invite_hash))
                
                print(f"  ✅ Successfully joined via invite link")
                return {
                    'success': True,
                    'method': 'invite_link',
                    'error': None
                }
            
            return {
                'success': False,
                'method': 'invite_link',
                'error': 'Not an invite link'
            }
            
        except Exception as e:
            print(f"  ❌ Invite link join failed: {e}")
            return {
                'success': False,
                'method': 'invite_link',
                'error': str(e)
            }
    
    async def _try_forum_channel_join(self, channel_identifier: str) -> dict:
        """Handle forum channels with topic IDs."""
        try:
            print(f"  📋 Strategy 4: Forum channel join {channel_identifier}")
            
            # Split channel and topic ID
            if '/' in channel_identifier:
                channel_part = channel_identifier.split('/')[0]
                topic_id = channel_identifier.split('/')[1]
                
                # First join the main channel
                main_result = await self._try_direct_join(channel_part)
                
                if main_result['success']:
                    print(f"  ✅ Joined main channel, topic ID: {topic_id}")
                    return {
                        'success': True,
                        'method': 'forum_channel_join',
                        'error': None,
                        'topic_id': topic_id
                    }
                else:
                    return main_result
            
            return {
                'success': False,
                'method': 'forum_channel_join',
                'error': 'Invalid forum channel format'
            }
            
        except Exception as e:
            print(f"  ❌ Forum channel join failed: {e}")
            return {
                'success': False,
                'method': 'forum_channel_join',
                'error': str(e)
            }
    
    async def _try_private_channel_access(self, channel_identifier: str) -> dict:
        """Handle private channels with special access requirements."""
        try:
            print(f"  📋 Strategy 5: Private channel access {channel_identifier}")
            
            # For private channels, we need to:
            # 1. Check if we need to send a join request
            # 2. Handle captcha if required
            # 3. Wait for approval
            
            # Try to get channel info first
            try:
                channel = await self.client.get_entity(channel_identifier)
                
                # Check if we're already a member
                participant = await self.client.get_participants(channel, limit=1)
                if participant:
                    print(f"  ✅ Already a member of {channel_identifier}")
                    return {
                        'success': True,
                        'method': 'already_member',
                        'error': None
                    }
                
            except Exception:
                pass
            
            # For private channels, we might need special handling
            print(f"  ⚠️ Private channel {channel_identifier} requires special access")
            return {
                'success': False,
                'method': 'private_channel_access',
                'error': 'Requires special access procedure',
                'requires_verification': True,
                'next_steps': [
                    'Send join request',
                    'Complete captcha if required',
                    'Wait for admin approval'
                ]
            }
            
        except Exception as e:
            print(f"  ❌ Private channel access failed: {e}")
            return {
                'success': False,
                'method': 'private_channel_access',
                'error': str(e)
            }
    
    async def handle_captcha(self, channel_identifier: str, captcha_data: dict) -> bool:
        """Handle captcha challenges."""
        try:
            print(f"  🧩 Worker {self.worker_id}: Handling captcha for {channel_identifier}")
            
            # This would need to be implemented based on the specific captcha type
            # For now, we'll log it and return False
            print(f"  ⚠️ Captcha handling not implemented yet")
            return False
            
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Error handling captcha: {e}")
            return False
    
    async def send_join_request(self, channel_identifier: str) -> bool:
        """Send a join request for private channels."""
        try:
            print(f"  📝 Worker {self.worker_id}: Sending join request for {channel_identifier}")
            
            # This would need to be implemented based on the channel's requirements
            # For now, we'll log it and return False
            print(f"  ⚠️ Join request sending not implemented yet")
            return False
            
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Error sending join request: {e}")
            return False

async def test_enhanced_joiner():
    """Test the enhanced channel joiner with problematic channels."""
    print("🧪 TESTING ENHANCED CHANNEL JOINER")
    print("=" * 50)
    
    # Problematic channels to test
    test_channels = [
        "@impacting",
        "@sectormarket/109", 
        "@social",
        "@sectormarket/20",
        "@sectormarket/10",
        "@instaempiremarket",
        "@memermarket",
        "@MarketPlace_666"
    ]
    
    print(f"\n📋 TESTING CHANNELS:")
    for channel in test_channels:
        print(f"  • {channel}")
    
    print(f"\n⚠️ NOTE: This is a test - no actual joining will occur")
    print(f"   The enhanced joiner will be integrated into the worker system")
    
    print(f"\n🔧 INTEGRATION PLAN:")
    print("=" * 25)
    print("1. Add EnhancedChannelJoiner to worker_client.py")
    print("2. Update posting service to use enhanced joining")
    print("3. Add captcha handling capabilities")
    print("4. Implement join request sending")
    print("5. Add retry logic with different strategies")
    
    print(f"\n🎯 EXPECTED IMPROVEMENTS:")
    print("=" * 30)
    print("• Handle forum channels with topic IDs")
    print("• Support private channel join requests")
    print("• Handle captcha challenges")
    print("• Multiple joining strategies")
    print("• Better error handling and recovery")

if __name__ == "__main__":
    asyncio.run(test_enhanced_joiner())
