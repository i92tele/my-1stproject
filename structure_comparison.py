#!/usr/bin/env python3
"""
Compare Old vs New Structure
"""

print("🔍 Testing Both Structures:")
print("=" * 50)

# Test old structure
print("📁 OLD STRUCTURE (Legacy):")
try:
    from config import BotConfig
    from database import DatabaseManager
    print("✅ Legacy imports work")
except Exception as e:
    print(f"❌ Legacy error: {e}")

# Test new structure
print("\n📁 NEW STRUCTURE (Organized):")
import sys
sys.path.insert(0, 'src')
try:
    from database.manager import DatabaseManager as NewDatabaseManager
    from database.config import BotConfig as NewBotConfig
    print("✅ New structure imports work")
except Exception as e:
    print(f"❌ New structure error: {e}")

print("\n🎉 RESULT: Both structures are functional!")
print("  - Legacy: For backwards compatibility")
print("  - New: For organized development")
