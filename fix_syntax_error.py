#!/usr/bin/env python3
"""
Fix Syntax Error in manager.py

This script fixes the syntax error in manager.py where a cursor.execute() statement
is outside of the try-except block.
"""

import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def fix_syntax_error():
    """Fix the syntax error in manager.py."""
    logger.info("🔧 FIXING SYNTAX ERROR IN MANAGER.PY")
    
    try:
        # Read the file
        with open('src/database/manager.py', 'r') as f:
            content = f.read()
        
        # Find the problematic section
        # We're looking for the admin_slot_destinations table creation that's outside the try block
        problematic_section = "        # Create admin_slot_destinations table\n        cursor.execute('''"
        fixed_section = "                # Create admin_slot_destinations table\n                cursor.execute('''"
        
        # Replace the problematic section
        if problematic_section in content:
            fixed_content = content.replace(problematic_section, fixed_section)
            
            # Write the fixed content back
            with open('src/database/manager.py', 'w') as f:
                f.write(fixed_content)
            
            logger.info("✅ Successfully fixed syntax error in manager.py")
            return True
        else:
            logger.warning("⚠️ Could not find the problematic section")
            return False
        
    except Exception as e:
        logger.error(f"❌ Error fixing syntax error: {e}")
        return False

def verify_syntax():
    """Verify that the syntax is correct by importing the module."""
    logger.info("\n🧪 VERIFYING SYNTAX")
    
    try:
        # Try to import the module
        import importlib.util
        spec = importlib.util.spec_from_file_location("manager", "src/database/manager.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        logger.info("✅ Syntax verification passed")
        return True
    except SyntaxError as e:
        logger.error(f"❌ Syntax error still exists: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Other error during verification: {e}")
        return False

def main():
    """Main function."""
    logger.info("🔧 SYNTAX ERROR FIX")
    logger.info("=" * 60)
    
    # Fix the syntax error
    fixed = fix_syntax_error()
    
    if fixed:
        # Verify the syntax
        verified = verify_syntax()
        
        if verified:
            logger.info("\n✅ FIX SUCCESSFUL")
            logger.info("The syntax error has been fixed and verified.")
        else:
            logger.error("\n❌ FIX INCOMPLETE")
            logger.error("The syntax error was fixed, but verification failed.")
    else:
        logger.error("\n❌ FIX FAILED")
        logger.error("Could not fix the syntax error.")
    
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
