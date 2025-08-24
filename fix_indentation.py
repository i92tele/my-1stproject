#!/usr/bin/env python3
"""
Fix Indentation Error

This script fixes the indentation error in manager.py line 204.
"""

def fix_indentation():
    """Fix the indentation error in manager.py."""
    print("🔧 FIXING INDENTATION ERROR")
    print("=" * 50)
    
    try:
        # Read the file
        with open('src/database/manager.py', 'r') as f:
            lines = f.readlines()
        
        print(f"📋 Read {len(lines)} lines from manager.py")
        
        # Find and fix the problematic lines around line 204
        fixed_lines = []
        in_problematic_section = False
        
        for i, line in enumerate(lines, 1):
            # Check if we're in the problematic section
            if 'admin_slot_destinations' in line and 'CREATE TABLE' in line:
                in_problematic_section = True
                print(f"🔍 Found problematic section at line {i}")
            
            # Fix indentation for the problematic section
            if in_problematic_section:
                if line.strip().startswith('#'):
                    # Comment lines should have proper indentation
                    if line.startswith('                        #'):
                        fixed_lines.append(line)
                    else:
                        # Fix comment indentation
                        fixed_lines.append('                        ' + line.lstrip())
                elif line.strip().startswith('cursor.execute'):
                    # SQL execution lines should have proper indentation
                    if line.startswith('                        cursor.execute'):
                        fixed_lines.append(line)
                    else:
                        # Fix SQL execution indentation
                        fixed_lines.append('                        ' + line.lstrip())
                elif line.strip().startswith('try:'):
                    # Try block should have proper indentation
                    if line.startswith('                        try:'):
                        fixed_lines.append(line)
                    else:
                        # Fix try block indentation
                        fixed_lines.append('                        ' + line.lstrip())
                elif line.strip().startswith('except'):
                    # Except block should have proper indentation
                    if line.startswith('                        except'):
                        fixed_lines.append(line)
                    else:
                        # Fix except block indentation
                        fixed_lines.append('                        ' + line.lstrip())
                elif line.strip().startswith('pass'):
                    # Pass statement should have proper indentation
                    if line.startswith('                            pass'):
                        fixed_lines.append(line)
                    else:
                        # Fix pass statement indentation
                        fixed_lines.append('                            ' + line.lstrip())
                elif line.strip() == '':
                    # Empty lines should be preserved
                    fixed_lines.append(line)
                elif line.strip().startswith('conn.commit'):
                    # End of problematic section
                    in_problematic_section = False
                    fixed_lines.append(line)
                else:
                    # Other lines in the section
                    fixed_lines.append(line)
            else:
                # Not in problematic section, keep as is
                fixed_lines.append(line)
        
        # Write the fixed file
        with open('src/database/manager.py', 'w') as f:
            f.writelines(fixed_lines)
        
        print("✅ Fixed indentation in manager.py")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing indentation: {e}")
        return False

def test_syntax():
    """Test that the file has correct syntax after fixing."""
    print("\n🧪 TESTING SYNTAX")
    print("=" * 50)
    
    try:
        # Try to import the module
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Try to import the database manager
        from src.database.manager import DatabaseManager
        
        print("✅ Syntax is correct - DatabaseManager imported successfully")
        return True
        
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        return False
    except Exception as e:
        print(f"❌ Other error: {e}")
        return False

def main():
    """Main function."""
    print("🔧 FIXING INDENTATION ERROR IN MANAGER.PY")
    print("=" * 60)
    
    # Fix indentation
    fixed = fix_indentation()
    
    if fixed:
        # Test syntax
        syntax_ok = test_syntax()
        
        print("\n📊 FIX RESULTS:")
        print("=" * 60)
        
        results = [
            ("Indentation Fix", fixed),
            ("Syntax Test", syntax_ok)
        ]
        
        all_passed = True
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name}: {status}")
            if not result:
                all_passed = False
        
        print("\n🎯 FINAL STATUS:")
        print("=" * 60)
        
        if all_passed:
            print("🎉 ALL FIXES SUCCESSFUL!")
            print("✅ Indentation error is fixed")
            print("✅ Syntax is correct")
            print("✅ Database manager can be imported")
            print("✅ Destination management should work")
        else:
            print("❌ SOME FIXES FAILED")
            print("❌ Check the results above")
    else:
        print("❌ Indentation fix failed")
    
    print("\n🔄 NEXT STEPS:")
    print("1. Run destination test again")
    print("2. If successful, restart the bot")
    print("3. Test destination selection in admin slots")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
