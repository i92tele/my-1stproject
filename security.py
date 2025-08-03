from datetime import datetime, timedelta
from typing import Optional, Dict, List
import secrets
import logging
import re
import hashlib

class SecurityManager:
    """Enhanced security management for the bot."""
    
    def __init__(self, config, db, logger):
        self.config = config
        self.db = db
        self.logger = logger
        self.rate_limiters = {}
        self.blocked_users = set()
        self.suspicious_activities = {}
        
        # Security patterns
        self.sql_injection_patterns = [
            r'(\b(union|select|insert|update|delete|drop|create|alter)\b)',
            r'(\b(or|and)\b\s+\d+\s*=\s*\d+)',
            r'(\b(union|select|insert|update|delete|drop|create|alter)\b.*\b(union|select|insert|update|delete|drop|create|alter)\b)',
            r'(\b(union|select|insert|update|delete|drop|create|alter)\b.*\b(or|and)\b)',
            r'(\b(union|select|insert|update|delete|drop|create|alter)\b.*\b(or|and)\b.*\d+\s*=\s*\d+)',
            r'(\b(union|select|insert|update|delete|drop|create|alter)\b.*\b(or|and)\b.*\b(union|select|insert|update|delete|drop|create|alter)\b)',
            r'(\b(union|select|insert|update|delete|drop|create|alter)\b.*\b(or|and)\b.*\b(union|select|insert|update|delete|drop|create|alter)\b.*\d+\s*=\s*\d+)',
            r'(\b(union|select|insert|update|delete|drop|create|alter)\b.*\b(or|and)\b.*\b(union|select|insert|update|delete|drop|create|alter)\b.*\b(or|and)\b)',
            r'(\b(union|select|insert|update|delete|drop|create|alter)\b.*\b(or|and)\b.*\b(union|select|insert|update|delete|drop|create|alter)\b.*\b(or|and)\b.*\d+\s*=\s*\d+)',
            r'(\b(union|select|insert|update|delete|drop|create|alter)\b.*\b(or|and)\b.*\b(union|select|insert|update|delete|drop|create|alter)\b.*\b(or|and)\b.*\b(union|select|insert|update|delete|drop|create|alter)\b)'
        ]
        
        self.xss_patterns = [
            r'<script[^>]*>.*?</script>',
            r'<iframe[^>]*>.*?</iframe>',
            r'<object[^>]*>.*?</object>',
            r'<embed[^>]*>.*?</embed>',
            r'<applet[^>]*>.*?</applet>',
            r'<form[^>]*>.*?</form>',
            r'<input[^>]*>',
            r'<textarea[^>]*>.*?</textarea>',
            r'<select[^>]*>.*?</select>',
            r'<button[^>]*>.*?</button>',
            r'<link[^>]*>',
            r'<meta[^>]*>',
            r'<style[^>]*>.*?</style>',
            r'<link[^>]*>',
            r'<base[^>]*>',
            r'<title[^>]*>.*?</title>',
            r'<head[^>]*>.*?</head>',
            r'<body[^>]*>.*?</body>',
            r'<html[^>]*>.*?</html>',
            r'<!DOCTYPE[^>]*>',
            r'<![CDATA[.*?]]>',
            r'<!--.*?-->',
            r'<!\[CDATA\[.*?\]\]>',
            r'<!\[CDATA\[.*?\]\]>',
            r'<!\[CDATA\[.*?\]\]>',
            r'<!\[CDATA\[.*?\]\]>',
            r'<!\[CDATA\[.*?\]\]>',
            r'<!\[CDATA\[.*?\]\]>'
        ]
    
    async def check_rate_limit(self, user_id: int, action: str, limit: int = 10, window: int = 60) -> bool:
        """Check if user has exceeded rate limit."""
        key = f"{user_id}:{action}"
        current_time = datetime.now()
        
        if key not in self.rate_limiters:
            self.rate_limiters[key] = []
        
        # Clean old entries
        self.rate_limiters[key] = [
            timestamp for timestamp in self.rate_limiters[key]
            if (current_time - timestamp).seconds < window
        ]
        
        if len(self.rate_limiters[key]) >= limit:
            await self.log_security_event({
                'type': 'rate_limit_exceeded',
                'user_id': user_id,
                'action': action,
                'limit': limit,
                'window': window
            })
            return False
            
        self.rate_limiters[key].append(current_time)
        return True
    
    def sanitize_input(self, text: str, max_length: int = 500) -> str:
        """Sanitize user input to prevent XSS and injection attacks."""
        if not text:
            return ""
        
        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char == '\n')
        
        # Check for SQL injection patterns
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                self.logger.warning(f"Potential SQL injection detected: {text[:100]}")
                return ""
        
        # Check for XSS patterns
        for pattern in self.xss_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                self.logger.warning(f"Potential XSS detected: {text[:100]}")
                return ""
        
        # Limit length
        text = text[:max_length]
        
        # Basic HTML entity encoding
        text = text.replace('<', '&lt;').replace('>', '&gt;')
        
        return text
    
    def validate_user_id(self, user_id) -> bool:
        """Validate user ID format."""
        try:
            user_id = int(user_id)
            return 100000000 <= user_id <= 999999999999  # Telegram user ID range
        except (ValueError, TypeError):
            return False
    
    def validate_payment_amount(self, amount: float) -> bool:
        """Validate payment amount."""
        try:
            amount = float(amount)
            return 0.01 <= amount <= 10000.0  # Reasonable payment range
        except (ValueError, TypeError):
            return False
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(length)
    
    def hash_sensitive_data(self, data: str) -> str:
        """Hash sensitive data for storage."""
        return hashlib.sha256(data.encode()).hexdigest()
    
    async def check_user_suspicious_activity(self, user_id: int) -> Dict:
        """Check for suspicious user activity."""
        current_time = datetime.now()
        
        if user_id not in self.suspicious_activities:
            self.suspicious_activities[user_id] = []
        
        # Clean old activities (older than 24 hours)
        self.suspicious_activities[user_id] = [
            activity for activity in self.suspicious_activities[user_id]
            if (current_time - activity['timestamp']).seconds < 86400
        ]
        
        # Count recent suspicious activities
        recent_activities = len(self.suspicious_activities[user_id])
        
        return {
            'is_suspicious': recent_activities > 5,
            'activity_count': recent_activities,
            'should_block': recent_activities > 10
        }
    
    async def log_security_event(self, event_data: Dict) -> None:
        """Log security event to database."""
        try:
            event_data['timestamp'] = datetime.now()
            event_data['hash'] = self.hash_sensitive_data(str(event_data))
            
            # Log to database if available
            if hasattr(self.db, 'log_security_event'):
                await self.db.log_security_event(event_data)
            
            # Log to console
            self.logger.warning(f"Security event: {event_data}")
            
        except Exception as e:
            self.logger.error(f"Error logging security event: {e}")
    
    async def block_user(self, user_id: int, reason: str) -> bool:
        """Block a user for security reasons."""
        try:
            self.blocked_users.add(user_id)
            await self.log_security_event({
                'type': 'user_blocked',
                'user_id': user_id,
                'reason': reason
            })
            return True
        except Exception as e:
            self.logger.error(f"Error blocking user {user_id}: {e}")
            return False
    
    def is_user_blocked(self, user_id: int) -> bool:
        """Check if user is blocked."""
        return user_id in self.blocked_users
    
    async def validate_payment_data(self, payment_data: Dict) -> Dict:
        """Validate payment data for security."""
        errors = []
        
        # Validate user ID
        if not self.validate_user_id(payment_data.get('user_id')):
            errors.append("Invalid user ID")
        
        # Validate amount
        if not self.validate_payment_amount(payment_data.get('amount_usd', 0)):
            errors.append("Invalid payment amount")
        
        # Validate cryptocurrency
        valid_cryptos = ['TON', 'BTC', 'ETH', 'SOL', 'LTC', 'USDT', 'USDC']
        if payment_data.get('cryptocurrency') not in valid_cryptos:
            errors.append("Invalid cryptocurrency")
        
        # Validate wallet address format
        wallet_address = payment_data.get('wallet_address', '')
        if not wallet_address or len(wallet_address) < 10:
            errors.append("Invalid wallet address")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }