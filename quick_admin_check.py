#!/usr/bin/env python3
"""
Quick Admin Ads Check
Simple script to check admin ads status without complex imports
"""
import sqlite3
import json

def quick_admin_check():
    """Quick check of admin ads status."""
    print("🎯 **QUICK ADMIN ADS CHECK**")
    print("=" * 50)
    
    try:
        # Connect to database
        conn = sqlite3.connect('bot_database.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get admin slots
        cursor.execute('''
            SELECT slot_number, content, destinations, is_active, created_at, updated_at
            FROM admin_ad_slots
            ORDER BY slot_number
        ''')
        
        slots = cursor.fetchall()
        
        if not slots:
            print("❌ No admin slots found")
            return
        
        print(f"✅ Found {len(slots)} admin slots")
        
        # Analyze slots
        active_count = 0
        inactive_count = 0
        total_destinations = 0
        slots_with_content = 0
        
        print(f"\n📊 **ADMIN SLOTS STATUS**")
        print("-" * 40)
        
        for slot in slots:
            slot_number = slot['slot_number']
            is_active = slot['is_active']
            content = slot['content'] or ''
            destinations_json = slot['destinations'] or '[]'
            
            # Parse destinations
            try:
                destinations = json.loads(destinations_json)
            except:
                destinations = []
            
            status_icon = "✅" if is_active else "⏸️"
            content_icon = "📝" if content else "❌"
            dest_count = len(destinations)
            
            if is_active:
                active_count += 1
                total_destinations += dest_count
            else:
                inactive_count += 1
            
            if content:
                slots_with_content += 1
            
            # Show slot info
            content_preview = content[:30] + '...' if len(content) > 30 else content
            print(f"{status_icon} Slot {slot_number}: {dest_count} groups {content_icon}")
            if content:
                print(f"   📝 Content: {content_preview}")
            if destinations:
                dest_names = [d.get('destination_name', 'Unknown') for d in destinations[:3]]
                print(f"   🎯 Groups: {', '.join(dest_names)}")
                if len(destinations) > 3:
                    print(f"   ... and {len(destinations) - 3} more")
            print()
        
        # Summary
        print(f"📈 **SUMMARY**")
        print("-" * 20)
        print(f"Total Slots: {len(slots)}")
        print(f"Active Slots: {active_count}")
        print(f"Inactive Slots: {inactive_count}")
        print(f"Slots with Content: {slots_with_content}")
        print(f"Total Groups Being Posted To: {total_destinations}")
        
        if active_count > 0 and total_destinations > 0:
            avg_groups = total_destinations / active_count
            print(f"Average Groups per Active Slot: {avg_groups:.1f}")
        
        # Check managed groups
        print(f"\n📋 **MANAGED GROUPS INFO**")
        print("-" * 30)
        
        cursor.execute('SELECT COUNT(*) as count FROM managed_groups')
        total_groups = cursor.fetchone()['count']
        print(f"Total Managed Groups: {total_groups}")
        
        # Groups by category
        cursor.execute('''
            SELECT category, COUNT(*) as count 
            FROM managed_groups 
            GROUP BY category 
            ORDER BY count DESC
        ''')
        
        categories = cursor.fetchall()
        print(f"Groups by Category:")
        for cat in categories:
            print(f"  • {cat['category']}: {cat['count']} groups")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def quick_status():
    """Quick status check without complex analysis."""
    try:
        import sqlite3
        import json
        
        conn = sqlite3.connect('bot_database.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Quick admin ads count
        cursor.execute('SELECT COUNT(*) as total, SUM(is_active) as active FROM admin_ad_slots')
        admin_result = cursor.fetchone()
        
        # Quick user ads count  
        cursor.execute('SELECT COUNT(*) as total FROM ad_slots WHERE is_active = 1')
        user_result = cursor.fetchone()
        
        # Quick worker status
        cursor.execute('SELECT COUNT(*) as total FROM workers WHERE is_active = 1')
        worker_result = cursor.fetchone()
        
        print(f"📊 QUICK STATUS:")
        print(f"├─ Admin Ads: {admin_result['active'] or 0}/{admin_result['total'] or 0} active")
        print(f"├─ User Ads: {user_result['total'] or 0} active")
        print(f"└─ Workers: {worker_result['total'] or 0} active")
        
        conn.close()
        
    except Exception as e:
        print(f"Status check error: {e}")

if __name__ == "__main__":
    import asyncio
    print("🎯 **ADMIN ADS & SYSTEM STATUS**")
    print("=" * 40)
    asyncio.run(quick_status())
    print("")
    quick_admin_check()
