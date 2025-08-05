#!/usr/bin/env python3
"""
AutoFarming Bot Project Cleanup Script

This script analyzes the project structure and:
1. Identifies the optimal bot entry point
2. Removes duplicate and unused files
3. Organizes remaining files logically
4. Updates import paths if needed
5. Creates a clean project structure

Usage: python3 cleanup_project.py
"""

import os
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Set, Tuple
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cleanup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ProjectCleanup:
    """Comprehensive project cleanup and reorganization."""
    
    def __init__(self):
        self.project_root = Path('.')
        self.backup_dir = self.project_root / 'backups' / 'cleanup_backup'
        self.files_to_remove = []
        self.files_to_move = {}
        self.import_updates = {}
        
    def analyze_project_structure(self) -> Dict[str, any]:
        """Analyze current project structure and identify issues."""
        logger.info("🔍 Analyzing project structure...")
        
        analysis = {
            'entry_points': [],
            'duplicates': [],
            'unused_files': [],
            'worker_files': [],
            'fix_files': [],
            'enhanced_files': [],
            'startup_scripts': [],
            'recommendations': []
        }
        
        # Find all Python files
        python_files = list(self.project_root.rglob('*.py'))
        
        # Analyze entry points
        for file_path in python_files:
            if file_path.name in ['main.py', 'bot.py', 'src/bot.py']:
                analysis['entry_points'].append(str(file_path))
            
            # Find startup scripts
            if file_path.name.startswith('start_'):
                analysis['startup_scripts'].append(str(file_path))
            
            # Find worker-related files
            if 'worker' in file_path.name.lower():
                analysis['worker_files'].append(str(file_path))
            
            # Find fix files
            if file_path.name.startswith('fix_'):
                analysis['fix_files'].append(str(file_path))
            
            # Find enhanced files
            if file_path.name.startswith('enhanced_'):
                analysis['enhanced_files'].append(str(file_path))
        
        # Identify duplicates
        analysis['duplicates'] = self._find_duplicates(python_files)
        
        # Identify unused files
        analysis['unused_files'] = self._find_unused_files(python_files)
        
        return analysis
    
    def _find_duplicates(self, python_files: List[Path]) -> List[Tuple[str, str]]:
        """Find duplicate files with similar functionality."""
        duplicates = []
        
        # Check for duplicate entry points
        entry_points = [f for f in python_files if f.name in ['bot.py', 'main.py']]
        if len(entry_points) > 1:
            duplicates.append(('bot.py', 'src/bot.py'))
        
        # Check for duplicate command files
        command_files = [f for f in python_files if 'command' in f.name.lower()]
        for file1 in command_files:
            for file2 in command_files:
                if file1 != file2 and file1.name.replace('_', '') == file2.name.replace('_', ''):
                    duplicates.append((str(file1), str(file2)))
        
        return duplicates
    
    def _find_unused_files(self, python_files: List[Path]) -> List[str]:
        """Find files that are likely unused."""
        unused = []
        
        # Files that are likely temporary or development
        temp_patterns = [
            'test_', 'temp_', 'backup_', 'old_', 'debug_',
            'fix_', 'enhanced_', 'quick_', 'simple_'
        ]
        
        for file_path in python_files:
            filename = file_path.name.lower()
            
            # Skip main files
            if filename in ['bot.py', 'main.py', 'config.py', 'database.py']:
                continue
            
            # Check if file matches temp patterns
            if any(pattern in filename for pattern in temp_patterns):
                unused.append(str(file_path))
        
        return unused
    
    def determine_optimal_entry_point(self, entry_points: List[str]) -> str:
        """Determine the best entry point to use."""
        logger.info("🎯 Determining optimal entry point...")
        
        # Priority order: src/bot.py > bot.py > main.py
        priority_order = ['src/bot.py', 'bot.py', 'main.py']
        
        for preferred in priority_order:
            if preferred in entry_points:
                logger.info(f"✅ Selected {preferred} as main entry point")
                return preferred
        
        # If none found, use the first available
        if entry_points:
            logger.info(f"⚠️ Using {entry_points[0]} as entry point")
            return entry_points[0]
        
        logger.error("❌ No suitable entry point found!")
        return None
    
    def create_backup(self):
        """Create backup of current project state."""
        logger.info("💾 Creating backup...")
        
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy all Python files to backup
        for py_file in self.project_root.rglob('*.py'):
            if py_file.is_file():
                backup_path = self.backup_dir / py_file.relative_to(self.project_root)
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(py_file, backup_path)
        
        logger.info(f"✅ Backup created at {self.backup_dir}")
    
    def remove_duplicate_files(self, duplicates: List[Tuple[str, str]]):
        """Remove duplicate files, keeping the better version."""
        logger.info("🗑️ Removing duplicate files...")
        
        for file1, file2 in duplicates:
            # Determine which file to keep
            keep_file = self._determine_better_file(file1, file2)
            remove_file = file2 if keep_file == file1 else file1
            
            logger.info(f"Removing duplicate: {remove_file} (keeping {keep_file})")
            
            # Move to backup instead of deleting
            backup_path = self.backup_dir / Path(remove_file).name
            if os.path.exists(remove_file):
                shutil.move(remove_file, backup_path)
                self.files_to_remove.append(remove_file)
    
    def _determine_better_file(self, file1: str, file2: str) -> str:
        """Determine which file is better to keep."""
        # Prefer src/ directory files
        if 'src/' in file1 and 'src/' not in file2:
            return file1
        elif 'src/' in file2 and 'src/' not in file1:
            return file2
        
        # Prefer shorter names
        if len(file1) < len(file2):
            return file1
        else:
            return file2
    
    def remove_unused_files(self, unused_files: List[str]):
        """Remove unused files."""
        logger.info("🗑️ Removing unused files...")
        
        for file_path in unused_files:
            if os.path.exists(file_path):
                logger.info(f"Removing unused file: {file_path}")
                
                # Move to backup instead of deleting
                backup_path = self.backup_dir / Path(file_path).name
                shutil.move(file_path, backup_path)
                self.files_to_remove.append(file_path)
    
    def organize_project_structure(self):
        """Reorganize project into optimal structure."""
        logger.info("📁 Reorganizing project structure...")
        
        # Create optimal directory structure
        directories = [
            'src/',
            'src/commands/',
            'src/services/',
            'src/utils/',
            'config/',
            'docs/',
            'scripts/',
            'tests/',
            'logs/',
            'data/',
            'sessions/'
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        # Move files to appropriate directories
        self._move_files_to_directories()
    
    def _move_files_to_directories(self):
        """Move files to their appropriate directories."""
        move_operations = {
            # Move command files
            'commands/user_commands.py': 'src/commands/user.py',
            'commands/admin_commands.py': 'src/commands/admin.py',
            'commands/forwarding_commands.py': 'src/commands/forwarding.py',
            
            # Move service files
            'src/posting_service.py': 'src/services/posting.py',
            'src/payment_processor.py': 'src/services/payment.py',
            'src/worker_manager.py': 'src/services/worker.py',
            
            # Move utility files
            'src/ui_manager.py': 'src/utils/ui.py',
            'src/error_handler.py': 'src/utils/error.py',
            'src/rate_limiter.py': 'src/utils/rate_limit.py',
            
            # Move configuration files
            'config.py': 'src/config.py',
        }
        
        for source, destination in move_operations.items():
            if os.path.exists(source):
                logger.info(f"Moving {source} to {destination}")
                Path(destination).parent.mkdir(parents=True, exist_ok=True)
                shutil.move(source, destination)
                self.files_to_move[source] = destination
    
    def update_import_paths(self):
        """Update import paths after file reorganization."""
        logger.info("🔧 Updating import paths...")
        
        # Find all Python files
        python_files = list(self.project_root.rglob('*.py'))
        
        for file_path in python_files:
            if file_path.is_file():
                self._update_file_imports(file_path)
    
    def _update_file_imports(self, file_path: Path):
        """Update imports in a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Update common import patterns
            import_updates = {
                'from commands import': 'from src.commands import',
                'from src.commands import user_commands': 'from src.commands import user',
                'from src.commands import admin_commands': 'from src.commands import admin',
                'from src.commands import forwarding_commands': 'from src.commands import forwarding',
                'from src.posting_service import': 'from src.services.posting import',
                'from src.payment_processor import': 'from src.services.payment import',
                'from src.worker_manager import': 'from src.services.worker import',
            }
            
            for old_import, new_import in import_updates.items():
                content = content.replace(old_import, new_import)
            
            # Only write if content changed
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"Updated imports in {file_path}")
                
        except Exception as e:
            logger.warning(f"Could not update imports in {file_path}: {e}")
    
    def create_optimal_structure(self):
        """Create the optimal project structure."""
        logger.info("🏗️ Creating optimal project structure...")
        
        # Create main entry point
        self._create_main_entry_point()
        
        # Create requirements.txt if missing
        if not os.path.exists('requirements.txt'):
            self._create_requirements_file()
        
        # Create README.md if missing
        if not os.path.exists('README.md'):
            self._create_readme_file()
        
        # Create .env template if missing
        if not os.path.exists('config/.env'):
            self._create_env_template()
    
    def _create_main_entry_point(self):
        """Create the main entry point file."""
        main_content = '''#!/usr/bin/env python3
"""
AutoFarming Bot - Main Entry Point

This is the main entry point for the AutoFarming Bot.
Run this file to start the bot: python3 main.py
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv('config/.env')

# Import bot components
from src.config import BotConfig
from src.database import DatabaseManager
from src.services.worker import WorkerManager
from src.services.payment import PaymentProcessor
from src.services.posting import PostingService
from src.commands import user, admin, forwarding

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AutoFarmingBot:
    """Main bot application class."""
    
    def __init__(self):
        self.config = BotConfig.load_from_env()
        self.db = DatabaseManager("bot_database.db", logger)
        self.worker_manager = None
        self.payment_processor = None
        self.posting_service = None
        
    async def initialize(self):
        """Initialize all bot components."""
        logger.info("🚀 Initializing AutoFarming Bot...")
        
        # Initialize database
        await self.db.initialize()
        logger.info("✅ Database initialized")
        
        # Initialize services
        self.worker_manager = WorkerManager(self.db, logger)
        self.payment_processor = PaymentProcessor(self.db, logger)
        self.posting_service = PostingService(self.db, self.worker_manager, logger)
        
        await self.worker_manager.initialize_workers()
        await self.payment_processor.initialize()
        await self.posting_service.initialize()
        
        logger.info("✅ All services initialized")
    
    async def run(self):
        """Run the bot."""
        try:
            await self.initialize()
            logger.info("🎉 Bot is running! Press Ctrl+C to stop.")
            
            # Keep the bot running
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("🛑 Shutting down bot...")
        except Exception as e:
            logger.error(f"❌ Bot crashed: {e}")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up resources."""
        logger.info("🧹 Cleaning up...")
        
        if self.worker_manager:
            await self.worker_manager.close_all_workers()
        
        if self.payment_processor:
            await self.payment_processor.close()
        
        if self.posting_service:
            await self.posting_service.stop()
        
        if self.db:
            await self.db.close()
        
        logger.info("✅ Cleanup complete")

async def main():
    """Main function."""
    # Create necessary directories
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    os.makedirs('sessions', exist_ok=True)
    
    # Create and run bot
    bot = AutoFarmingBot()
    await bot.run()

if __name__ == '__main__':
    asyncio.run(main())
'''
        
        with open('main.py', 'w') as f:
            f.write(main_content)
        
        logger.info("✅ Created main.py as primary entry point")
    
    def _create_requirements_file(self):
        """Create requirements.txt file."""
        requirements_content = '''# Core Bot Dependencies
python-telegram-bot==20.6
python-dotenv==1.0.0
aiohttp==3.9.1

# Database
asyncpg==0.29.0

# Cryptocurrency and Blockchain
requests==2.31.0
cryptography==41.0.7

# Optional Dependencies
redis==5.0.1
psutil==5.9.6

# Development and Testing
pytest==7.4.3
pytest-asyncio==0.21.1
'''
        
        with open('requirements.txt', 'w') as f:
            f.write(requirements_content)
        
        logger.info("✅ Created requirements.txt")
    
    def _create_readme_file(self):
        """Create README.md file."""
        readme_content = '''# AutoFarming Bot

A sophisticated Telegram bot for automated ad posting with cryptocurrency payments.

## Features

- 🤖 Automated ad posting with worker rotation
- 💰 TON cryptocurrency payment processing
- 📊 Comprehensive analytics and monitoring
- 🔧 Admin controls and user management
- 🛡️ Anti-ban protection and cooldown management

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp config/env_template.txt config/.env
   # Edit config/.env with your actual values
   ```

3. **Run the bot:**
   ```bash
   python3 main.py
   ```

## Project Structure

```
├── main.py                 # Main entry point
├── src/                    # Source code
│   ├── commands/          # Command handlers
│   ├── services/          # Core services
│   └── utils/             # Utilities
├── config/                # Configuration files
├── docs/                  # Documentation
├── scripts/               # Utility scripts
├── tests/                 # Test files
├── logs/                  # Log files
└── data/                  # Data files
```

## Configuration

Required environment variables:
- `BOT_TOKEN`: Your Telegram bot token
- `ADMIN_ID`: Your Telegram user ID
- `TON_ADDRESS`: Your TON wallet address
- `DATABASE_URL`: Database connection string

## Documentation

See the `docs/` directory for detailed documentation.

## License

This project is proprietary software.
'''
        
        with open('README.md', 'w') as f:
            f.write(readme_content)
        
        logger.info("✅ Created README.md")
    
    def _create_env_template(self):
        """Create .env template file."""
        env_template = '''# Bot Configuration
BOT_TOKEN=your_telegram_bot_token_here
ADMIN_ID=your_admin_user_id_here

# Database Configuration
DATABASE_URL=sqlite:///bot_database.db

# Cryptocurrency Wallets
TON_ADDRESS=EQD...your_ton_wallet_address_here
BTC_ADDRESS=your_bitcoin_address_here
ETH_ADDRESS=your_ethereum_address_here

# Security Keys
ENCRYPTION_KEY=your_32_character_encryption_key_here
SECRET_KEY=your_secret_key_here

# Worker Accounts (Add your worker credentials)
WORKER_1_API_ID=your_worker_1_api_id
WORKER_1_API_HASH=your_worker_1_api_hash
WORKER_1_PHONE=your_worker_1_phone_number

WORKER_2_API_ID=your_worker_2_api_id
WORKER_2_API_HASH=your_worker_2_api_hash
WORKER_2_PHONE=your_worker_2_phone_number

# Environment
ENVIRONMENT=development
'''
        
        os.makedirs('config', exist_ok=True)
        with open('config/.env', 'w') as f:
            f.write(env_template)
        
        logger.info("✅ Created config/.env template")
    
    def generate_cleanup_report(self, analysis: Dict[str, any]):
        """Generate a report of the cleanup operation."""
        logger.info("📊 Generating cleanup report...")
        
        report = f"""
# AutoFarming Bot - Cleanup Report

## Summary
- **Entry Point**: {analysis.get('entry_points', [])}
- **Files Removed**: {len(self.files_to_remove)}
- **Files Moved**: {len(self.files_to_move)}
- **Import Updates**: {len(self.import_updates)}

## Files Removed
{chr(10).join(f"- {file}" for file in self.files_to_remove)}

## Files Moved
{chr(10).join(f"- {old} → {new}" for old, new in self.files_to_move.items())}

## Recommendations
{chr(10).join(f"- {rec}" for rec in analysis.get('recommendations', []))}

## Next Steps
1. Configure config/.env with actual values
2. Test the bot with: python3 main.py
3. Run health checks: python3 health_check.py
4. Test integration: python3 test_integration.py

## Backup Location
All removed files are backed up in: {self.backup_dir}
"""
        
        with open('CLEANUP_REPORT.md', 'w') as f:
            f.write(report)
        
        logger.info("✅ Cleanup report generated: CLEANUP_REPORT.md")
    
    def run_cleanup(self):
        """Run the complete cleanup process."""
        logger.info("🚀 Starting AutoFarming Bot project cleanup...")
        
        # Create backup
        self.create_backup()
        
        # Analyze project structure
        analysis = self.analyze_project_structure()
        
        # Determine optimal entry point
        optimal_entry = self.determine_optimal_entry_point(analysis['entry_points'])
        analysis['recommendations'].append(f"Use {optimal_entry} as main entry point")
        
        # Remove duplicates
        self.remove_duplicate_files(analysis['duplicates'])
        
        # Remove unused files
        self.remove_unused_files(analysis['unused_files'])
        
        # Organize project structure
        self.organize_project_structure()
        
        # Update import paths
        self.update_import_paths()
        
        # Create optimal structure
        self.create_optimal_structure()
        
        # Generate report
        self.generate_cleanup_report(analysis)
        
        logger.info("🎉 Cleanup completed successfully!")
        logger.info("📋 See CLEANUP_REPORT.md for details")

def main():
    """Main function."""
    cleanup = ProjectCleanup()
    cleanup.run_cleanup()

if __name__ == '__main__':
    main() 