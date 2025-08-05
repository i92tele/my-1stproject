#!/usr/bin/env python3
"""
Quick Health Check for AutoFarming Bot

This script performs a quick health check focusing on critical issues
that would prevent the bot from starting.

Usage: python3 quick_health_check.py
"""

import os
import sys
import importlib
from datetime import datetime

def check_critical_issues():
    """Check for critical issues that would prevent bot startup."""
    print("🔍 Quick Health Check for AutoFarming Bot")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    issues_found = []
    warnings = []
    
    # 1. Check if .env file exists
    print("📁 Checking config/.env file...")
    if not os.path.exists('config/.env'):
        issues_found.append("❌ config/.env file not found")
        print("   💡 Create config/.env file with required variables")
    else:
        print("   ✅ config/.env file exists")
    
    # 2. Check required environment variables
    print("\n🔧 Checking environment variables...")
    required_vars = ['BOT_TOKEN', 'ADMIN_ID', 'DATABASE_URL']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        issues_found.append(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print(f"   ❌ Missing: {', '.join(missing_vars)}")
        print("   💡 Set these variables in config/.env")
    else:
        print("   ✅ All required environment variables are set")
    
    # 3. Check critical dependencies
    print("\n📦 Checking critical dependencies...")
    critical_packages = ['python-telegram-bot', 'python-dotenv', 'aiohttp']
    missing_packages = []
    
    for package in critical_packages:
        try:
            importlib.import_module(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        issues_found.append(f"❌ Missing critical packages: {', '.join(missing_packages)}")
        print(f"   ❌ Missing: {', '.join(missing_packages)}")
        print("   💡 Install with: pip install " + " ".join(missing_packages))
    else:
        print("   ✅ All critical packages are installed")
    
    # 4. Check critical files
    print("\n📄 Checking critical files...")
    critical_files = ['bot.py', 'config.py', 'database.py']
    missing_files = []
    
    for file in critical_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        issues_found.append(f"❌ Missing critical files: {', '.join(missing_files)}")
        print(f"   ❌ Missing: {', '.join(missing_files)}")
    else:
        print("   ✅ All critical files exist")
    
    # 5. Check for syntax errors in critical files
    print("\n🔍 Checking for syntax errors...")
    syntax_errors = []
    
    for file in critical_files:
        if os.path.exists(file):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    compile(f.read(), file, 'exec')
            except SyntaxError as e:
                syntax_errors.append(f"{file}: {e}")
    
    if syntax_errors:
        issues_found.append(f"❌ Syntax errors found: {', '.join(syntax_errors)}")
        print(f"   ❌ Syntax errors: {', '.join(syntax_errors)}")
    else:
        print("   ✅ No syntax errors found")
    
    # 6. Check imports
    print("\n📚 Checking critical imports...")
    critical_modules = ['config', 'database']
    import_errors = []
    
    for module in critical_modules:
        try:
            importlib.import_module(module)
        except ImportError as e:
            import_errors.append(f"{module}: {e}")
    
    if import_errors:
        issues_found.append(f"❌ Import errors: {', '.join(import_errors)}")
        print(f"   ❌ Import errors: {', '.join(import_errors)}")
    else:
        print("   ✅ Critical modules can be imported")
    
    # 7. Check commands directory
    print("\n⌨️ Checking commands directory...")
    if not os.path.exists('commands'):
        issues_found.append("❌ commands directory not found")
        print("   ❌ commands directory missing")
    elif not os.path.exists('commands/__init__.py'):
        issues_found.append("❌ commands/__init__.py not found")
        print("   ❌ commands/__init__.py missing")
    else:
        print("   ✅ commands directory structure looks good")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 QUICK HEALTH CHECK SUMMARY")
    print("=" * 50)
    
    if issues_found:
        print("🚨 CRITICAL ISSUES FOUND:")
        for issue in issues_found:
            print(f"   {issue}")
        print("\n💡 RECOMMENDED ACTIONS:")
        print("   1. Fix all critical issues above")
        print("   2. Run full health check: python3 health_check.py")
        print("   3. Test bot startup: python3 bot.py")
        return False
    else:
        print("✅ No critical issues found!")
        print("🎉 Your bot should be able to start successfully")
        print("\n💡 Next steps:")
        print("   1. Run full health check: python3 health_check.py")
        print("   2. Test bot startup: python3 bot.py")
        return True

if __name__ == "__main__":
    success = check_critical_issues()
    sys.exit(0 if success else 1) 