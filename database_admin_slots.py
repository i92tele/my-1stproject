#!/usr/bin/env python3
"""
Database Methods for Admin Ad Slots
Handles database operations for admin-specific ad slots
"""

import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

logger = logging.getLogger(__name__)

class AdminSlotDatabase:
    """Database operations for admin ad slots."""
    
    def __init__(self, db_path: str, logger):
        self.db_path = db_path
        self.logger = logger
        
    async def migrate_admin_slots_table(self) -> bool:
        """Migrate existing admin_ad_slots table to add missing columns."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_ad_slots'")
            if not cursor.fetchone():
                conn.close()
                return True  # Table doesn't exist, no migration needed
            
            # Add missing columns one by one
            columns_to_add = [
                ('interval_minutes', 'INTEGER DEFAULT 60'),
                ('last_sent_at', 'TIMESTAMP'),
                ('assigned_worker_id', 'INTEGER DEFAULT 1')
            ]
            
            for column_name, column_def in columns_to_add:
                try:
                    cursor.execute(f'ALTER TABLE admin_ad_slots ADD COLUMN {column_name} {column_def}')
                    self.logger.info(f"Added column {column_name} to admin_ad_slots")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e).lower():
                        self.logger.debug(f"Column {column_name} already exists")
                    else:
                        self.logger.error(f"Error adding column {column_name}: {e}")
            
            conn.commit()
            conn.close()
            self.logger.info("Admin slots table migration completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Error migrating admin slots table: {e}")
            return False
        
    async def create_admin_ad_slots(self) -> bool:
        """Create the initial 20 admin ad slots."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create admin slots table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admin_ad_slots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slot_number INTEGER UNIQUE,
                    content TEXT,
                    destinations TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    interval_minutes INTEGER DEFAULT 60,
                    last_sent_at TIMESTAMP,
                    assigned_worker_id INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Add missing columns to existing table (migration)
            try:
                cursor.execute('ALTER TABLE admin_ad_slots ADD COLUMN interval_minutes INTEGER DEFAULT 60')
            except sqlite3.OperationalError:
                pass  # Column already exists
                
            try:
                cursor.execute('ALTER TABLE admin_ad_slots ADD COLUMN last_sent_at TIMESTAMP')
            except sqlite3.OperationalError:
                pass  # Column already exists
                
            try:
                cursor.execute('ALTER TABLE admin_ad_slots ADD COLUMN assigned_worker_id INTEGER DEFAULT 1')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            # Check if slots already exist
            cursor.execute('SELECT COUNT(*) FROM admin_ad_slots')
            existing_count = cursor.fetchone()[0]
            
            if existing_count == 0:
                # Create 20 admin slots
                for i in range(1, 21):
                    cursor.execute('''
                        INSERT INTO admin_ad_slots (slot_number, content, destinations, is_active)
                        VALUES (?, ?, ?, ?)
                    ''', (i, None, json.dumps([]), True))
                
                conn.commit()
                self.logger.info(f"Created 20 admin ad slots")
            
            conn.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating admin ad slots: {e}")
            return False
            
    async def get_admin_ad_slots(self) -> List[Dict[str, Any]]:
        """Get all admin ad slots."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, slot_number, content, destinations, is_active, created_at, updated_at
                FROM admin_ad_slots
                ORDER BY slot_number
            ''')
            
            slots = []
            for row in cursor.fetchall():
                slot = dict(row)
                # Parse destinations JSON
                try:
                    slot['destinations'] = json.loads(slot['destinations']) if slot['destinations'] else []
                except:
                    slot['destinations'] = []
                slots.append(slot)
            
            conn.close()
            return slots
            
        except Exception as e:
            self.logger.error(f"Error getting admin ad slots: {e}")
            return []
            
    async def get_admin_ad_slot(self, slot_number: int) -> Optional[Dict[str, Any]]:
        """Get a specific admin ad slot."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, slot_number, content, destinations, is_active, created_at, updated_at
                FROM admin_ad_slots
                WHERE slot_number = ?
            ''', (slot_number,))
            
            row = cursor.fetchone()
            if row:
                slot = dict(row)
                # Parse destinations JSON
                try:
                    slot['destinations'] = json.loads(slot['destinations']) if slot['destinations'] else []
                except:
                    slot['destinations'] = []
                conn.close()
                return slot
            
            conn.close()
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting admin ad slot {slot_number}: {e}")
            return None
            
    async def update_admin_slot_content(self, slot_id: int, content: str) -> bool:
        """Update content for an admin slot."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE admin_ad_slots
                SET content = ?, updated_at = ?
                WHERE id = ?
            ''', (content, datetime.now(), slot_id))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Updated content for admin slot {slot_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating admin slot content: {e}")
            return False
            
    async def update_admin_slot_destinations(self, slot_id: int, destinations: List[Dict[str, Any]]) -> bool:
        """Update destinations for an admin slot."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            destinations_json = json.dumps(destinations)
            cursor.execute('''
                UPDATE admin_ad_slots
                SET destinations = ?, updated_at = ?
                WHERE id = ?
            ''', (destinations_json, datetime.now(), slot_id))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Updated destinations for admin slot {slot_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating admin slot destinations: {e}")
            return False
            
    async def update_admin_slot_status(self, slot_id: int, is_active: bool) -> bool:
        """Update active status for an admin slot."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE admin_ad_slots
                SET is_active = ?, updated_at = ?
                WHERE id = ?
            ''', (is_active, datetime.now(), slot_id))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Updated status for admin slot {slot_id} to {is_active}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating admin slot status: {e}")
            return False
            
    async def get_admin_slot_destinations(self, slot_id: int) -> List[Dict[str, Any]]:
        """Get destinations for a specific admin slot."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT destinations FROM admin_ad_slots WHERE id = ?', (slot_id,))
            row = cursor.fetchone()
            
            if row and row[0]:
                try:
                    destinations = json.loads(row[0])
                    conn.close()
                    return destinations
                except:
                    conn.close()
                    return []
            
            conn.close()
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting admin slot destinations: {e}")
            return []
            
    async def get_admin_slots_stats(self) -> Dict[str, Any]:
        """Get statistics for admin slots."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get basic stats
            cursor.execute('SELECT COUNT(*) FROM admin_ad_slots')
            total_slots = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM admin_ad_slots WHERE is_active = 1')
            active_slots = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM admin_ad_slots WHERE content IS NOT NULL AND content != ""')
            slots_with_content = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM admin_ad_slots WHERE destinations IS NOT NULL AND destinations != "[]"')
            slots_with_destinations = cursor.fetchone()[0]
            
            # Get posting stats (this would need to be implemented with actual posting tracking)
            posts_today = 0
            posts_week = 0
            posts_month = 0
            
            # Get top performing slots (placeholder)
            top_slots = []
            
            conn.close()
            
            return {
                'total_slots': total_slots,
                'active_slots': active_slots,
                'slots_with_content': slots_with_content,
                'slots_with_destinations': slots_with_destinations,
                'posts_today': posts_today,
                'posts_week': posts_week,
                'posts_month': posts_month,
                'top_slots': top_slots
            }
            
        except Exception as e:
            self.logger.error(f"Error getting admin slots stats: {e}")
            return {}
            
    async def delete_admin_slot(self, slot_id: int) -> bool:
        """Delete an admin slot."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM admin_ad_slots WHERE id = ?', (slot_id,))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Deleted admin slot {slot_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting admin slot: {e}")
            return False
    
    async def update_admin_slot_interval(self, slot_id: int, interval_minutes: int) -> bool:
        """Update the posting interval for an admin slot."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE admin_ad_slots 
                SET interval_minutes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (interval_minutes, slot_id))
            
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
            
        except Exception as e:
            self.logger.error(f"Error updating admin slot interval: {e}")
            return False
    
    async def get_admin_slot_by_number(self, slot_number: int) -> Optional[Dict[str, Any]]:
        """Get admin slot by slot number."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM admin_ad_slots WHERE slot_number = ?', (slot_number,))
            row = cursor.fetchone()
            
            conn.close()
            return dict(row) if row else None
            
        except Exception as e:
            self.logger.error(f"Error getting admin slot by number: {e}")
            return None
            
    async def add_admin_slot_destination(self, slot_id: int, destination_data: Dict[str, Any]) -> bool:
        """Add a destination to an admin slot."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current destinations
            cursor.execute('SELECT destinations FROM admin_ad_slots WHERE id = ?', (slot_id,))
            row = cursor.fetchone()
            
            if row and row[0]:
                try:
                    destinations = json.loads(row[0])
                except:
                    destinations = []
            else:
                destinations = []
            
            # Check if destination already exists
            dest_id = destination_data.get('destination_id')
            if not any(dest.get('destination_id') == dest_id for dest in destinations):
                destinations.append(destination_data)
                
                # Update the slot
                destinations_json = json.dumps(destinations)
                cursor.execute('''
                    UPDATE admin_ad_slots
                    SET destinations = ?, updated_at = ?
                    WHERE id = ?
                ''', (destinations_json, datetime.now(), slot_id))
                
                conn.commit()
                self.logger.info(f"Added destination {dest_id} to admin slot {slot_id}")
            
            conn.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding destination to admin slot: {e}")
            return False
            
    async def remove_admin_slot_destination(self, slot_id: int, destination_id: str) -> bool:
        """Remove a destination from an admin slot."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current destinations
            cursor.execute('SELECT destinations FROM admin_ad_slots WHERE id = ?', (slot_id,))
            row = cursor.fetchone()
            
            if row and row[0]:
                try:
                    destinations = json.loads(row[0])
                except:
                    destinations = []
            else:
                destinations = []
            
            # Remove the destination
            destinations = [dest for dest in destinations if dest.get('destination_id') != destination_id]
            
            # Update the slot
            destinations_json = json.dumps(destinations)
            cursor.execute('''
                UPDATE admin_ad_slots
                SET destinations = ?, updated_at = ?
                WHERE id = ?
            ''', (destinations_json, datetime.now(), slot_id))
            
            conn.commit()
            self.logger.info(f"Removed destination {destination_id} from admin slot {slot_id}")
            
            conn.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing destination from admin slot: {e}")
            return False
            
    async def clear_admin_slot_destinations(self, slot_id: int) -> bool:
        """Clear all destinations from an admin slot."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE admin_ad_slots
                SET destinations = ?, updated_at = ?
                WHERE id = ?
            ''', (json.dumps([]), datetime.now(), slot_id))
            
            conn.commit()
            self.logger.info(f"Cleared all destinations from admin slot {slot_id}")
            
            conn.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Error clearing destinations from admin slot: {e}")
            return False
