#!/usr/bin/env python3
"""
Worker Health Monitor
Monitors health and performance of 50+ workers
"""

import asyncio
import sqlite3
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional
from enhanced_worker_manager import EnhancedWorkerManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WorkerHealthMonitor:
    def __init__(self, db_path: str = 'bot_database.db'):
        self.db_path = db_path
        self.manager = EnhancedWorkerManager(db_path)
        
    async def check_worker_health(self) -> Dict:
        """Check health of all workers."""
        logger.info("🏥 Checking worker health...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all workers
            cursor.execute('''
                SELECT w.worker_id, w.username, w.is_active, w.is_registered,
                       wh.status, wh.error_count, wh.ban_count,
                       wu.hourly_posts, wu.daily_posts, wu.hourly_limit, wu.daily_limit
                FROM workers w
                LEFT JOIN worker_health wh ON w.worker_id = wh.worker_id
                LEFT JOIN worker_usage wu ON w.worker_id = wu.worker_id
                WHERE w.is_active = 1
                ORDER BY w.worker_id
            ''')
            
            workers = cursor.fetchall()
            conn.close()
            
            health_summary = {
                'total_workers': len(workers),
                'healthy_workers': 0,
                'unhealthy_workers': 0,
                'banned_workers': 0,
                'overloaded_workers': 0,
                'worker_details': []
            }
            
            for worker_data in workers:
                worker_id, username, is_active, is_registered, status, error_count, ban_count, hourly_posts, daily_posts, hourly_limit, daily_limit = worker_data
                
                worker_detail = {
                    'worker_id': worker_id,
                    'username': username,
                    'status': status or 'unknown',
                    'error_count': error_count or 0,
                    'ban_count': ban_count or 0,
                    'hourly_usage': f"{hourly_posts or 0}/{hourly_limit or 15}",
                    'daily_usage': f"{daily_posts or 0}/{daily_limit or 100}",
                    'health_score': 100
                }
                
                # Calculate health score
                health_score = 100
                
                # Deduct points for errors
                if error_count and error_count > 0:
                    health_score -= min(error_count * 10, 50)
                
                # Deduct points for bans
                if ban_count and ban_count > 0:
                    health_score -= min(ban_count * 20, 50)
                
                # Deduct points for overload
                if hourly_posts and hourly_limit and hourly_posts > hourly_limit * 0.8:
                    health_score -= 20
                
                if daily_posts and daily_limit and daily_posts > daily_limit * 0.8:
                    health_score -= 20
                
                worker_detail['health_score'] = max(health_score, 0)
                
                # Categorize worker
                if worker_detail['health_score'] >= 80:
                    health_summary['healthy_workers'] += 1
                else:
                    health_summary['unhealthy_workers'] += 1
                
                if ban_count and ban_count > 0:
                    health_summary['banned_workers'] += 1
                
                if (hourly_posts and hourly_limit and hourly_posts > hourly_limit * 0.9) or \
                   (daily_posts and daily_limit and daily_posts > daily_limit * 0.9):
                    health_summary['overloaded_workers'] += 1
                
                health_summary['worker_details'].append(worker_detail)
            
            logger.info(f"📊 Health Summary: {health_summary['healthy_workers']} healthy, {health_summary['unhealthy_workers']} unhealthy")
            return health_summary
            
        except Exception as e:
            logger.error(f"❌ Error checking worker health: {e}")
            return {}
    
    async def test_worker_connectivity(self) -> Dict:
        """Test connectivity of all workers."""
        logger.info("🔌 Testing worker connectivity...")
        
        # Load registered workers
        active_count = await self.manager.load_registered_workers()
        
        if active_count == 0:
            logger.warning("⚠️ No workers loaded for connectivity test")
            return {'total': 0, 'connected': 0, 'failed': 0}
        
        # Test all workers
        health = await self.manager.test_all_workers()
        
        # Update health status in database
        await self._update_health_status(health)
        
        return health
    
    async def _update_health_status(self, health: Dict):
        """Update worker health status in database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Update last check time for all workers
            cursor.execute('''
                UPDATE worker_health 
                SET last_check = CURRENT_TIMESTAMP
                WHERE worker_id IN (SELECT worker_id FROM workers WHERE is_active = 1)
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Error updating health status: {e}")
    
    async def get_worker_performance(self) -> Dict:
        """Get performance metrics for all workers."""
        logger.info("📈 Getting worker performance metrics...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get performance data for last 24 hours
            yesterday = datetime.now() - timedelta(days=1)
            
            cursor.execute('''
                SELECT w.worker_id, w.username,
                       COUNT(*) as total_posts,
                       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_posts,
                       SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_posts
                FROM workers w
                LEFT JOIN worker_posts wp ON w.worker_id = wp.worker_id
                WHERE w.is_active = 1 
                AND wp.created_at >= ?
                GROUP BY w.worker_id, w.username
                ORDER BY total_posts DESC
            ''', (yesterday.isoformat(),))
            
            performance_data = cursor.fetchall()
            conn.close()
            
            performance_summary = {
                'total_workers': len(performance_data),
                'total_posts_24h': sum(row[2] for row in performance_data),
                'successful_posts_24h': sum(row[3] for row in performance_data),
                'failed_posts_24h': sum(row[4] for row in performance_data),
                'worker_performance': []
            }
            
            for row in performance_data:
                worker_id, username, total_posts, successful_posts, failed_posts = row
                
                success_rate = (successful_posts / total_posts * 100) if total_posts > 0 else 0
                
                performance_summary['worker_performance'].append({
                    'worker_id': worker_id,
                    'username': username,
                    'total_posts': total_posts,
                    'successful_posts': successful_posts,
                    'failed_posts': failed_posts,
                    'success_rate': round(success_rate, 2)
                })
            
            return performance_summary
            
        except Exception as e:
            logger.error(f"❌ Error getting performance metrics: {e}")
            return {}
    
    async def generate_health_report(self) -> str:
        """Generate a comprehensive health report."""
        logger.info("📋 Generating health report...")
        
        # Get health data
        health = await self.check_worker_health()
        connectivity = await self.test_worker_connectivity()
        performance = await self.get_worker_performance()
        
        # Generate report
        report = []
        report.append("🤖 WORKER HEALTH REPORT")
        report.append("=" * 50)
        report.append(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Health Summary
        report.append("🏥 HEALTH SUMMARY:")
        report.append(f"   Total Workers: {health.get('total_workers', 0)}")
        report.append(f"   Healthy: {health.get('healthy_workers', 0)}")
        report.append(f"   Unhealthy: {health.get('unhealthy_workers', 0)}")
        report.append(f"   Banned: {health.get('banned_workers', 0)}")
        report.append(f"   Overloaded: {health.get('overloaded_workers', 0)}")
        report.append("")
        
        # Connectivity Summary
        report.append("🔌 CONNECTIVITY:")
        report.append(f"   Connected: {connectivity.get('healthy', 0)}")
        report.append(f"   Failed: {connectivity.get('failed', 0)}")
        report.append("")
        
        # Performance Summary
        report.append("📈 PERFORMANCE (24h):")
        report.append(f"   Total Posts: {performance.get('total_posts_24h', 0)}")
        report.append(f"   Successful: {performance.get('successful_posts_24h', 0)}")
        report.append(f"   Failed: {performance.get('failed_posts_24h', 0)}")
        
        if performance.get('total_posts_24h', 0) > 0:
            overall_success_rate = (performance.get('successful_posts_24h', 0) / performance.get('total_posts_24h', 1)) * 100
            report.append(f"   Success Rate: {overall_success_rate:.1f}%")
        report.append("")
        
        # Top Performers
        if performance.get('worker_performance'):
            report.append("🏆 TOP PERFORMERS (24h):")
            top_performers = sorted(performance['worker_performance'], 
                                  key=lambda x: x['total_posts'], reverse=True)[:5]
            
            for i, worker in enumerate(top_performers, 1):
                report.append(f"   {i}. Worker {worker['worker_id']} (@{worker['username'] or 'No username'}): "
                            f"{worker['total_posts']} posts ({worker['success_rate']}% success)")
            report.append("")
        
        # Unhealthy Workers
        unhealthy_workers = [w for w in health.get('worker_details', []) if w['health_score'] < 80]
        if unhealthy_workers:
            report.append("⚠️ UNHEALTHY WORKERS:")
            for worker in unhealthy_workers[:10]:  # Show top 10
                report.append(f"   Worker {worker['worker_id']}: Score {worker['health_score']}, "
                            f"Errors: {worker['error_count']}, Bans: {worker['ban_count']}")
            report.append("")
        
        # Recommendations
        report.append("💡 RECOMMENDATIONS:")
        if health.get('unhealthy_workers', 0) > 0:
            report.append("   • Investigate unhealthy workers")
        if health.get('banned_workers', 0) > 0:
            report.append("   • Review banned workers and clear bans if appropriate")
        if health.get('overloaded_workers', 0) > 0:
            report.append("   • Consider adding more workers to reduce load")
        if connectivity.get('failed', 0) > 0:
            report.append("   • Check failed worker connections")
        
        return '\n'.join(report)

async def main():
    """Main function."""
    monitor = WorkerHealthMonitor()
    
    print("🏥 Worker Health Monitor")
    print("=" * 40)
    
    # Generate health report
    report = await monitor.generate_health_report()
    print(report)
    
    # Save report to file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"worker_health_report_{timestamp}.txt"
    
    with open(filename, 'w') as f:
        f.write(report)
    
    print(f"\n📄 Report saved to: {filename}")

if __name__ == "__main__":
    asyncio.run(main())
