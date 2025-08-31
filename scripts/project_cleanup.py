#!/usr/bin/env python3
"""
Project Cleanup Script
Organize temporary files and improve project structure
"""

import os
import shutil
import glob
from datetime import datetime

def create_backup():
    """Create a backup before cleanup."""
    backup_dir = f"backup_before_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    # Backup temporary files
    temp_patterns = [
        "fix_*.py",
        "test_*.py", 
        "debug_*.py",
        "analyze_*.py",
        "check_*.py",
        "verify_*.py"
    ]
    
    for pattern in temp_patterns:
        for file_path in glob.glob(pattern):
            if os.path.isfile(file_path):
                shutil.copy2(file_path, backup_dir)
                print(f"📦 Backed up: {file_path}")
    
    print(f"✅ Backup created: {backup_dir}")
    return backup_dir

def organize_scripts():
    """Organize utility scripts into proper directories."""
    scripts_dir = "scripts"
    os.makedirs(scripts_dir, exist_ok=True)
    
    # Create subdirectories
    subdirs = ["utils", "tests", "fixes", "debug", "analysis"]
    for subdir in subdirs:
        os.makedirs(os.path.join(scripts_dir, subdir), exist_ok=True)
    
    # Move files by category
    file_categories = {
        "fixes": ["fix_*.py"],
        "tests": ["test_*.py"],
        "debug": ["debug_*.py"],
        "analysis": ["analyze_*.py", "check_*.py", "verify_*.py"]
    }
    
    moved_files = []
    for category, patterns in file_categories.items():
        target_dir = os.path.join(scripts_dir, category)
        
        for pattern in patterns:
            for file_path in glob.glob(pattern):
                if os.path.isfile(file_path):
                    # Skip if it's a core project file
                    if any(skip in file_path for skip in ["bot.py", "main.py", "config/"]):
                        continue
                    
                    target_path = os.path.join(target_dir, os.path.basename(file_path))
                    
                    # Handle duplicates
                    if os.path.exists(target_path):
                        base, ext = os.path.splitext(target_path)
                        target_path = f"{base}_{datetime.now().strftime('%H%M%S')}{ext}"
                    
                    shutil.move(file_path, target_path)
                    moved_files.append((file_path, target_path))
                    print(f"📁 Moved: {file_path} → {target_path}")
    
    return moved_files

def cleanup_temp_directories():
    """Remove temporary directories."""
    temp_dirs = [
        "remaining_fixes_20250829_113434",
        "backup_before_github_restore"
    ]
    
    removed_dirs = []
    for dir_path in temp_dirs:
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                removed_dirs.append(dir_path)
                print(f"🗑️ Removed directory: {dir_path}")
            except Exception as e:
                print(f"⚠️ Could not remove {dir_path}: {e}")
    
    return removed_dirs

def cleanup_temp_files():
    """Remove temporary files that are no longer needed."""
    temp_files = [
        "*.log.bak",
        "*.tmp",
        "*.swp",
        "*.pyc",
        "__pycache__"
    ]
    
    removed_files = []
    for pattern in temp_files:
        for file_path in glob.glob(pattern):
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    removed_files.append(file_path)
                    print(f"🗑️ Removed: {file_path}")
                except Exception as e:
                    print(f"⚠️ Could not remove {file_path}: {e}")
    
    # Remove __pycache__ directories
    for root, dirs, files in os.walk("."):
        if "__pycache__" in dirs:
            cache_dir = os.path.join(root, "__pycache__")
            try:
                shutil.rmtree(cache_dir)
                removed_files.append(cache_dir)
                print(f"🗑️ Removed: {cache_dir}")
            except Exception as e:
                print(f"⚠️ Could not remove {cache_dir}: {e}")
    
    return removed_files

def update_documentation():
    """Update documentation to reflect cleanup."""
    readme_content = """# AutoFarming Bot - Project Structure

## 📁 Directory Structure

### Core Files
- `bot.py` - Main bot entry point
- `DEVELOPMENT_PROGRESS.md` - Development tracking
- `README.md` - Project overview
- `TODAYS_ACTION_PLAN.md` - Current session plan

### Source Code
- `src/` - Main source code
- `scheduler/` - Scheduler components
- `commands/` - Bot commands
- `config/` - Configuration files

### Scripts (Organized)
- `scripts/fixes/` - Database and code fixes
- `scripts/tests/` - Test scripts
- `scripts/debug/` - Debugging tools
- `scripts/analysis/` - Analysis scripts
- `scripts/utils/` - Utility functions

### Sessions
- `sessions/` - Daily session logs

### Data
- `bot_database.db` - Main database
- `scheduler.log` - Scheduler logs
- `health_check.log` - Health check logs

## 🧹 Recent Cleanup
- Temporary files organized into scripts/ subdirectories
- Duplicate files removed
- Project structure improved
- Documentation updated

Last cleanup: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    with open("PROJECT_STRUCTURE.md", "w") as f:
        f.write(readme_content)
    
    print("📝 Created: PROJECT_STRUCTURE.md")

def main():
    """Main cleanup process."""
    print("🧹 PROJECT CLEANUP STARTED")
    print("=" * 50)
    
    # Create backup
    backup_dir = create_backup()
    
    # Organize scripts
    print("\n📁 ORGANIZING SCRIPTS")
    print("-" * 30)
    moved_files = organize_scripts()
    
    # Cleanup temp directories
    print("\n🗑️ CLEANING TEMP DIRECTORIES")
    print("-" * 30)
    removed_dirs = cleanup_temp_directories()
    
    # Cleanup temp files
    print("\n🗑️ CLEANING TEMP FILES")
    print("-" * 30)
    removed_files = cleanup_temp_files()
    
    # Update documentation
    print("\n📝 UPDATING DOCUMENTATION")
    print("-" * 30)
    update_documentation()
    
    # Summary
    print("\n🎉 CLEANUP COMPLETE!")
    print("=" * 50)
    print(f"📦 Backup created: {backup_dir}")
    print(f"📁 Files moved: {len(moved_files)}")
    print(f"🗑️ Directories removed: {len(removed_dirs)}")
    print(f"🗑️ Files removed: {len(removed_files)}")
    print("📝 Documentation updated")
    
    print("\n📋 NEXT STEPS:")
    print("1. Review the organized scripts/ directory")
    print("2. Test that core functionality still works")
    print("3. Update session log with cleanup results")

if __name__ == "__main__":
    main()
