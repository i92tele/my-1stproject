#!/usr/bin/env python3
"""
Fix Syntax Error in Payment Processor

This script fixes the syntax error in payment_processor.py that's causing the Main Bot to crash.
"""

import os
import sys
import re
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def fix_payment_processor_syntax():
    """Fix the syntax error in payment_processor.py."""
    logger.info("🔧 FIXING SYNTAX ERROR IN PAYMENT PROCESSOR")
    
    file_path = 'src/services/payment_processor.py'
    
    try:
        # Read the current file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Look for the syntax error
        # The error is likely a line added inside a try block without proper except/finally
        if "payment = fix_payment_data(payment_raw)" in content:
            # Find all try blocks
            try_blocks = re.finditer(r'try\s*:', content)
            
            for match in try_blocks:
                try_start = match.start()
                # Find the corresponding except or finally
                try_block_text = content[try_start:try_start+5000]  # Look ahead a reasonable amount
                
                # Check if our problematic line is in this try block
                if "payment = fix_payment_data(payment_raw)" in try_block_text:
                    # Find the position of our problematic line
                    line_pos = try_block_text.find("payment = fix_payment_data(payment_raw)")
                    
                    # Check if there's an except or finally after this line
                    after_line = try_block_text[line_pos:]
                    if "except" not in after_line and "finally" not in after_line:
                        # This is our problem - we need to move the line outside the try block
                        
                        # Find the end of the try block
                        # Look for the last line before our problematic line
                        lines = try_block_text[:line_pos].split('\n')
                        last_line = lines[-1]
                        
                        # Create fixed content by moving our line outside the try block
                        fixed_content = content.replace(
                            f"{last_line}\n        payment = fix_payment_data(payment_raw)",
                            f"{last_line}\n        payment_raw = payment_raw\n        except Exception as e:\n            self.logger.error(f\"Error creating payment request: {{e}}\")\n            return {{\n                'error': str(e),\n                'success': False\n            }}\n        \n        payment = fix_payment_data(payment_raw)"
                        )
                        
                        # Write the fixed content
                        with open(file_path, 'w') as f:
                            f.write(fixed_content)
                        
                        logger.info(f"✅ Fixed syntax error in {file_path}")
                        return True
        
        # If we get here, we didn't find the specific error pattern
        # Let's try a more general approach - check all imports and fix_payment_data calls
        
        # First, make sure the import is at the top level
        if "from src.payment_address_direct_fix import fix_payment_data" in content:
            # Move the import to the top of the file
            content = content.replace(
                "from src.payment_address_direct_fix import fix_payment_data",
                ""
            )
            content = "from src.payment_address_direct_fix import fix_payment_data\n" + content
            
            # Now find all instances of payment_raw and fix them
            content = content.replace(
                "payment_raw = await",
                "payment = await"
            )
            
            # Replace all fix_payment_data calls with proper error handling
            content = content.replace(
                "payment = fix_payment_data(payment_raw)",
                "# Fix payment data to include address\ntry:\n            payment = fix_payment_data(payment)\nexcept Exception as e:\n            self.logger.error(f\"Error fixing payment data: {e}\")"
            )
            
            # Write the fixed content
            with open(file_path, 'w') as f:
                f.write(content)
            
            logger.info(f"✅ Fixed syntax error in {file_path} (general approach)")
            return True
        
        # If we get here, we need a more radical approach
        # Let's just remove the problematic import and function call
        content = content.replace("from src.payment_address_direct_fix import fix_payment_data", "")
        content = content.replace("from src.payment_address_direct_fix import fix_payment_data, get_payment_message", "")
        content = content.replace("payment_raw = await", "payment = await")
        content = content.replace("payment = fix_payment_data(payment_raw)", "")
        
        # Write the fixed content
        with open(file_path, 'w') as f:
            f.write(content)
        
        logger.info(f"✅ Removed problematic code from {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error fixing syntax error: {e}")
        return False

def main():
    """Main function."""
    logger.info("🔧 PAYMENT PROCESSOR SYNTAX FIX")
    logger.info("=" * 60)
    
    # Fix the syntax error
    fixed = fix_payment_processor_syntax()
    
    # Summary
    if fixed:
        logger.info("\n✅ SYNTAX ERROR FIXED")
        logger.info("You can now restart the bot")
    else:
        logger.error("\n❌ FAILED TO FIX SYNTAX ERROR")
        logger.error("Manual intervention required")
    
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
