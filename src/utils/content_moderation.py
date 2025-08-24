#!/usr/bin/env python3
import re
import logging
from typing import Dict, List, Tuple
from src.database.manager import DatabaseManager

class ContentModerator:
    """Content moderation and spam prevention."""
    
    def __init__(self, db: DatabaseManager, logger):
        self.db = db
        self.logger = logger
        
        # Spam keywords and patterns
        self.spam_keywords = [
            'buy now', 'limited time', 'act fast', 'click here', 'make money fast',
            'earn money', 'get rich', 'investment opportunity', 'crypto investment',
            'bitcoin investment', 'forex trading', 'binary options', 'mlm',
            'multi level marketing', 'pyramid scheme', 'get paid to click'
        ]
        
        # Inappropriate content patterns
        self.inappropriate_patterns = [
            r'\b(sex|porn|adult|xxx|nude)\b',
            r'\b(drugs|cocaine|heroin|weed)\b',
            r'\b(violence|kill|murder|attack)\b',
            r'\b(scam|fraud|fake|phishing)\b'
        ]
        
        # URL patterns
        self.url_patterns = [
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            r'www\.(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        ]
    
    async def moderate_content(self, content: str, user_id: int) -> Dict:
        """Moderate content and return moderation result."""
        try:
            issues = []
            severity = 'low'
            
            # Check for spam keywords
            spam_issues = self._check_spam_keywords(content)
            if spam_issues:
                issues.extend(spam_issues)
                severity = 'medium'
            
            # Check for inappropriate content
            inappropriate_issues = self._check_inappropriate_content(content)
            if inappropriate_issues:
                issues.extend(inappropriate_issues)
                severity = 'high'
            
            # Check for excessive URLs
            url_issues = self._check_url_spam(content)
            if url_issues:
                issues.extend(url_issues)
                severity = 'medium'
            
            # Check user's posting history
            user_issues = await self._check_user_history(user_id)
            if user_issues:
                issues.extend(user_issues)
                severity = 'high'
            
            # Determine if content should be blocked
            is_blocked = severity == 'high' or len(issues) > 3
            
            return {
                'is_blocked': is_blocked,
                'severity': severity,
                'issues': issues,
                'suggestions': self._get_suggestions(issues)
            }
            
        except Exception as e:
            self.logger.error(f"Error moderating content: {e}")
            return {'is_blocked': False, 'severity': 'low', 'issues': [], 'suggestions': []}
    
    def _check_spam_keywords(self, content: str) -> List[str]:
        """Check for spam keywords in content."""
        issues = []
        content_lower = content.lower()
        
        for keyword in self.spam_keywords:
            if keyword in content_lower:
                issues.append(f"Contains spam keyword: '{keyword}'")
        
        return issues
    
    def _check_inappropriate_content(self, content: str) -> List[str]:
        """Check for inappropriate content patterns."""
        issues = []
        
        for pattern in self.inappropriate_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                issues.append(f"Contains inappropriate content pattern")
        
        return issues
    
    def _check_url_spam(self, content: str) -> List[str]:
        """Check for excessive URLs in content."""
        issues = []
        
        url_count = 0
        for pattern in self.url_patterns:
            urls = re.findall(pattern, content)
            url_count += len(urls)
        
        if url_count > 2:
            issues.append(f"Too many URLs ({url_count} found)")
        
        return issues
    
    async def _check_user_history(self, user_id: int) -> List[str]:
        """Check user's posting history for suspicious patterns."""
        try:
            async with self.db.pool.acquire() as conn:
                # Get user's recent posts
                recent_posts = await conn.fetch('''
                    SELECT COUNT(*) as post_count, 
                           COUNT(CASE WHEN success = false THEN 1 END) as failed_posts
                    FROM ad_posts 
                    WHERE user_id = $1 AND created_at >= NOW() - INTERVAL '24 hours'
                ''', user_id)
                
                if recent_posts:
                    post_count = recent_posts[0]['post_count']
                    failed_posts = recent_posts[0]['failed_posts']
                    
                    issues = []
                    
                    # Check for excessive posting
                    if post_count > 50:
                        issues.append("Excessive posting in last 24 hours")
                    
                    # Check for high failure rate
                    if post_count > 0 and (failed_posts / post_count) > 0.8:
                        issues.append("High posting failure rate")
                    
                    return issues
                    
        except Exception as e:
            self.logger.error(f"Error checking user history: {e}")
        
        return []
    
    def _get_suggestions(self, issues: List[str]) -> List[str]:
        """Get suggestions for improving content."""
        suggestions = []
        
        if any('spam keyword' in issue for issue in issues):
            suggestions.append("Avoid using aggressive marketing language")
        
        if any('inappropriate' in issue for issue in issues):
            suggestions.append("Ensure content is appropriate for all audiences")
        
        if any('URL' in issue for issue in issues):
            suggestions.append("Limit the number of links in your ad")
        
        if any('excessive posting' in issue for issue in issues):
            suggestions.append("Space out your posts to avoid being flagged as spam")
        
        return suggestions
    
    async def log_moderation_event(self, user_id: int, content: str, result: Dict):
        """Log moderation event for analysis."""
        try:
            async with self.db.pool.acquire() as conn:
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS moderation_logs (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT REFERENCES users(user_id),
                        content_preview TEXT,
                        is_blocked BOOLEAN,
                        severity VARCHAR(20),
                        issues_count INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                content_preview = content[:100] + "..." if len(content) > 100 else content
                
                await conn.execute('''
                    INSERT INTO moderation_logs (user_id, content_preview, is_blocked, severity, issues_count)
                    VALUES ($1, $2, $3, $4, $5)
                ''', user_id, content_preview, result['is_blocked'], result['severity'], len(result['issues']))
                
        except Exception as e:
            self.logger.error(f"Error logging moderation event: {e}")
    
    async def get_moderation_stats(self) -> Dict:
        """Get moderation statistics."""
        try:
            async with self.db.pool.acquire() as conn:
                # Total moderated posts
                total_posts = await conn.fetchval('SELECT COUNT(*) FROM moderation_logs')
                
                # Blocked posts
                blocked_posts = await conn.fetchval('SELECT COUNT(*) FROM moderation_logs WHERE is_blocked = true')
                
                # Severity breakdown
                high_severity = await conn.fetchval('SELECT COUNT(*) FROM moderation_logs WHERE severity = \'high\'')
                medium_severity = await conn.fetchval('SELECT COUNT(*) FROM moderation_logs WHERE severity = \'medium\'')
                low_severity = await conn.fetchval('SELECT COUNT(*) FROM moderation_logs WHERE severity = \'low\'')
                
                return {
                    'total_posts': total_posts,
                    'blocked_posts': blocked_posts,
                    'block_rate': round((blocked_posts / total_posts * 100), 2) if total_posts > 0 else 0,
                    'high_severity': high_severity,
                    'medium_severity': medium_severity,
                    'low_severity': low_severity
                }
        except Exception as e:
            self.logger.error(f"Error getting moderation stats: {e}")
            return {} 