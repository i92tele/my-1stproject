#!/usr/bin/env python3
"""
Direct Indentation Fix

This script directly fixes the indentation issue at line 203-204 in manager.py
"""

def fix_indentation():
    """Fix the specific indentation issue at line 203-204."""
    print("🔧 FIXING INDENTATION ISSUE")
    print("=" * 50)
    
    try:
        # Read the file line by line
        with open('src/database/manager.py', 'r') as f:
            lines = f.readlines()
        
        # Fix the indentation for the problematic lines
        fixed_lines = []
        for i, line in enumerate(lines):
            # Check if this is one of the problematic lines
            if "# Create admin_slot_destinations table" in line:
                # Fix the indentation - remove 8 spaces (2 tabs)
                fixed_line = line[8:]
                fixed_lines.append(fixed_line)
            elif i > 0 and "# Create admin_slot_destinations table" in lines[i-1] and "cursor.execute" in line:
                # Fix the indentation for the next line too
                fixed_line = line[8:]
                fixed_lines.append(fixed_line)
            elif i > 1 and "cursor.execute" in lines[i-2] and "CREATE TABLE IF NOT EXISTS admin_slot_destinations" in line:
                # Fix the SQL query indentation
                fixed_line = line[8:]
                fixed_lines.append(fixed_line)
            elif i > 2 and "CREATE TABLE IF NOT EXISTS admin_slot_destinations" in lines[i-3] and "id INTEGER PRIMARY KEY" in line:
                # Fix the SQL query indentation (continued)
                fixed_line = line[8:]
                fixed_lines.append(fixed_line)
            elif "# Add updated_at column if it doesn't exist" in line:
                # Fix the indentation - remove 8 spaces (2 tabs)
                fixed_line = line[8:]
                fixed_lines.append(fixed_line)
            elif i > 0 and "# Add updated_at column if it doesn't exist" in lines[i-1]:
                # Fix the indentation for the next lines
                fixed_line = line[8:]
                fixed_lines.append(fixed_line)
            elif i > 1 and "try:" in lines[i-1] and "cursor.execute" in line and "ALTER TABLE" in line:
                # Fix the indentation for the ALTER TABLE line
                fixed_line = line[8:]
                fixed_lines.append(fixed_line)
            elif i > 2 and "ALTER TABLE" in lines[i-1] and "except" in line:
                # Fix the indentation for the except line
                fixed_line = line[8:]
                fixed_lines.append(fixed_line)
            elif i > 3 and "except" in lines[i-1] and "# Column already exists" in line:
                # Fix the indentation for the comment line
                fixed_line = line[8:]
                fixed_lines.append(fixed_line)
            elif i > 4 and "# Column already exists" in lines[i-1] and "pass" in line:
                # Fix the indentation for the pass line
                fixed_line = line[8:]
                fixed_lines.append(fixed_line)
            else:
                # Keep the line as is
                fixed_lines.append(line)
        
        # Write the fixed content back to the file
        with open('src/database/manager.py', 'w') as f:
            f.writelines(fixed_lines)
        
        print("✅ Fixed indentation in manager.py")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing indentation: {e}")
        return False

def main():
    """Main function."""
    print("🔧 DIRECT INDENTATION FIX")
    print("=" * 60)
    
    # Fix indentation
    fixed = fix_indentation()
    
    if fixed:
        print("✅ Indentation fixed successfully!")
        print("\n🔄 NEXT STEPS:")
        print("1. Run: python3 test_destination_final.py")
        print("2. If successful, restart the bot")
        print("3. Test admin destination selection")
    else:
        print("❌ Failed to fix indentation")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
