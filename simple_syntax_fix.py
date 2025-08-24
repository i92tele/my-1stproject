#!/usr/bin/env python3
"""
Simple Syntax Fix

Direct fix for the syntax error at line 204 in manager.py
"""

def fix_syntax_error():
    """Fix the specific syntax error at line 204."""
    print("🔧 FIXING SYNTAX ERROR AT LINE 204")
    print("=" * 50)
    
    try:
        # Read the entire file
        with open('src/database/manager.py', 'r') as f:
            lines = f.readlines()
        
        # Find the problematic section
        fixed_lines = []
        skip_mode = False
        
        for i, line in enumerate(lines):
            # Check if we're entering the problematic section
            if "# Create admin_slot_destinations table" in line:
                # Add this line
                fixed_lines.append(line)
                # Add a fixed version of the table creation
                fixed_lines.append("                        cursor.execute('''\n")
                fixed_lines.append("                            CREATE TABLE IF NOT EXISTS admin_slot_destinations (\n")
                fixed_lines.append("                                id INTEGER PRIMARY KEY AUTOINCREMENT,\n")
                fixed_lines.append("                                slot_id INTEGER,\n")
                fixed_lines.append("                                destination_type TEXT DEFAULT 'group',\n")
                fixed_lines.append("                                destination_id TEXT,\n")
                fixed_lines.append("                                destination_name TEXT,\n")
                fixed_lines.append("                                alias TEXT,\n")
                fixed_lines.append("                                is_active BOOLEAN DEFAULT 1,\n")
                fixed_lines.append("                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\n")
                fixed_lines.append("                                updated_at TEXT\n")
                fixed_lines.append("                            )\n")
                fixed_lines.append("                        ''')\n")
                
                # Skip until we find conn.commit()
                skip_mode = True
            elif skip_mode and "conn.commit()" in line:
                # Stop skipping and add this line
                skip_mode = False
                fixed_lines.append(line)
            elif not skip_mode:
                # Add non-problematic lines
                fixed_lines.append(line)
        
        # Write the fixed file
        with open('src/database/manager.py', 'w') as f:
            f.writelines(fixed_lines)
        
        print("✅ Fixed syntax error in manager.py")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing syntax: {e}")
        return False

def test_import():
    """Test if the file can be imported now."""
    print("\n🧪 TESTING IMPORT")
    print("=" * 50)
    
    try:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Clear any cached modules
        if 'src.database.manager' in sys.modules:
            del sys.modules['src.database.manager']
        
        from src.database.manager import DatabaseManager
        
        print("✅ Import successful!")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def main():
    """Main function."""
    print("🔧 SIMPLE SYNTAX FIX")
    print("=" * 60)
    
    # Fix syntax
    fixed = fix_syntax_error()
    
    if fixed:
        # Test import
        imported = test_import()
        
        print("\n📊 FIX RESULTS:")
        print("=" * 60)
        print(f"Syntax Fix: {'✅ PASSED' if fixed else '❌ FAILED'}")
        print(f"Import Test: {'✅ PASSED' if imported else '❌ FAILED'}")
        
        all_passed = fixed and imported
        
        if all_passed:
            print("\n🎉 SUCCESS!")
            print("✅ Syntax error is fixed")
            print("✅ Manager can be imported")
            print("✅ Ready to test destination management")
        else:
            print("\n❌ FAILED")
            print("❌ Issues remain")
    else:
        print("\n❌ SYNTAX FIX FAILED")
    
    print("\n🔄 NEXT STEPS:")
    if fixed and imported:
        print("1. Run: python3 test_destination_final.py")
        print("2. If successful, restart the bot")
        print("3. Test admin destination selection")
    else:
        print("1. Check manager.py manually")
        print("2. Fix remaining syntax issues")
    
    print("=" * 60)

if __name__ == "__main__":
    main()