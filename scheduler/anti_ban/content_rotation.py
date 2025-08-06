#!/usr/bin/env python3
"""
Content Rotation
Manages message content variation to avoid detection
"""

import random
import re
from typing import List, Dict, Any
from datetime import datetime

class ContentRotator:
    """Rotates and varies message content to avoid detection."""
    
    def __init__(self):
        self.emojis = ["��", "��", "⭐", "��", "��", "��", "✨", "🎉", "🏆", "💪"]
        self.prefixes = ["Check this out!", "Amazing offer!", "Don't miss this!", "Limited time!", "Exclusive!"]
        self.suffixes = ["DM for details", "Contact for more info", "Get in touch!", "Reach out!", "Message me!"]
        
    def rotate_message(self, original_message: str, user_id: int = None) -> str:
        """Rotate and vary message content."""
        if not original_message:
            return original_message
            
        # Add random emoji
        if random.random() < 0.7:  # 70% chance
            emoji = random.choice(self.emojis)
            original_message = f"{emoji} {original_message}"
            
        # Add random prefix
        if random.random() < 0.3:  # 30% chance
            prefix = random.choice(self.prefixes)
            original_message = f"{prefix}\n\n{original_message}"
            
        # Add random suffix
        if random.random() < 0.4:  # 40% chance
            suffix = random.choice(self.suffixes)
            original_message = f"{original_message}\n\n{suffix}"
            
        # Add timestamp variation
        if random.random() < 0.2:  # 20% chance
            timestamp = datetime.now().strftime("%H:%M")
            original_message = f"{original_message}\n\nPosted at {timestamp}"
            
        return original_message
        
    def add_user_specific_content(self, message: str, user_id: int) -> str:
        """Add user-specific content variations."""
        # Add user ID hash for tracking
        user_hash = hash(str(user_id)) % 1000
        if random.random() < 0.1:  # 10% chance
            message = f"{message}\n\nRef: {user_hash:03d}"
            
        return message
        
    def sanitize_message(self, message: str) -> str:
        """Sanitize message for posting."""
        # Remove excessive whitespace
        message = re.sub(r'\n\s*\n\s*\n', '\n\n', message)
        
        # Limit message length
        if len(message) > 4000:
            message = message[:3997] + "..."
            
        return message.strip()
