#!/usr/bin/env python3
"""
Production Deployment Script for AutoFarming Bot
Prepares the bot for production deployment
"""

import os
import sys
import logging
import subprocess
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProductionDeployment:
    def __init__(self):
        self.project_root = Path.cwd()
        self.deployment_log = []
        
    def log_step(self, step: str, status: str, details: str = ""):
        """Log a deployment step."""
        log_entry = {
            'step': step,
            'status': status,
            'details': details,
            'timestamp': datetime.now()
        }
        self.deployment_log.append(log_entry)
        status_icon = "✅" if status == "SUCCESS" else "❌" if status == "FAILED" else "⚠️"
        logger.info(f"{status_icon} {step}: {status}")
        if details:
            logger.info(f"   Details: {details}")
    
    def check_prerequisites(self):
        """Check deployment prerequisites."""
        logger.info("🔍 Checking Prerequisites...")
        
        # Check Python version
        if sys.version_info >= (3, 8):
            self.log_step("Python Version", "SUCCESS", f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        else:
            self.log_step("Python Version", "FAILED", "Python 3.8+ required")
            return False
        
        # Check virtual environment
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            self.log_step("Virtual Environment", "SUCCESS", "Virtual environment active")
        else:
            self.log_step("Virtual Environment", "WARNING", "No virtual environment detected")
        
        # Check critical files
        critical_files = ['main.py', 'src/bot.py', 'config/.env', 'requirements.txt']
        for file_path in critical_files:
            if os.path.exists(file_path):
                self.log_step(f"File: {file_path}", "SUCCESS", "File exists")
            else:
                self.log_step(f"File: {file_path}", "FAILED", "File missing")
                return False
        
        return True
    
    def validate_environment(self):
        """Validate environment configuration."""
        logger.info("🌍 Validating Environment...")
        
        try:
            from dotenv import load_dotenv
            load_dotenv('config/.env')
            
            # Check critical environment variables
            critical_vars = ['BOT_TOKEN', 'ADMIN_ID', 'TON_ADDRESS']
            for var in critical_vars:
                value = os.getenv(var)
                if value and value != f'your_{var.lower()}_here':
                    self.log_step(f"Environment: {var}", "SUCCESS", "Variable set")
                else:
                    self.log_step(f"Environment: {var}", "FAILED", "Variable not configured")
                    return False
            
            # Check optional variables
            optional_vars = ['WORKER_1_API_ID', 'WORKER_1_API_HASH', 'WORKER_1_PHONE']
            for var in optional_vars:
                value = os.getenv(var)
                if value:
                    self.log_step(f"Optional: {var}", "SUCCESS", "Variable set")
                else:
                    self.log_step(f"Optional: {var}", "WARNING", "Variable not set")
            
            return True
            
        except Exception as e:
            self.log_step("Environment Validation", "FAILED", str(e))
            return False
    
    def test_dependencies(self):
        """Test all dependencies."""
        logger.info("📦 Testing Dependencies...")
        
        try:
            # Test critical imports
            critical_imports = [
                'telegram',
                'dotenv',
                'aiohttp',
                'asyncio'
            ]
            
            for package in critical_imports:
                try:
                    __import__(package)
                    self.log_step(f"Import: {package}", "SUCCESS", "Import successful")
                except ImportError as e:
                    self.log_step(f"Import: {package}", "FAILED", str(e))
                    return False
            
            # Test bot components
            from src.config import BotConfig
            from src.database.manager import DatabaseManager
            from src.commands import user, admin
            
            config = BotConfig.load_from_env()
            self.log_step("Bot Components", "SUCCESS", "All components imported successfully")
            
            return True
            
        except Exception as e:
            self.log_step("Dependencies Test", "FAILED", str(e))
            return False
    
    def create_production_structure(self):
        """Create production-ready directory structure."""
        logger.info("📁 Creating Production Structure...")
        
        try:
            # Create production directories
            production_dirs = [
                'logs',
                'data',
                'backups',
                'sessions'
            ]
            
            for dir_path in production_dirs:
                Path(dir_path).mkdir(exist_ok=True)
                self.log_step(f"Directory: {dir_path}", "SUCCESS", "Directory created/verified")
            
            # Create log files
            log_files = [
                'logs/bot.log',
                'logs/errors.log',
                'logs/access.log'
            ]
            
            for log_file in log_files:
                Path(log_file).touch(exist_ok=True)
                self.log_step(f"Log File: {log_file}", "SUCCESS", "Log file created")
            
            return True
            
        except Exception as e:
            self.log_step("Production Structure", "FAILED", str(e))
            return False
    
    def create_startup_scripts(self):
        """Create production startup scripts."""
        logger.info("🚀 Creating Startup Scripts...")
        
        try:
            # Create main startup script
            startup_script = """#!/bin/bash
# AutoFarming Bot Production Startup Script

echo "🚀 Starting AutoFarming Bot..."

# Activate virtual environment
source venv/bin/activate

# Set environment
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Start the bot
python3 main.py
"""
            
            with open('start_bot.sh', 'w') as f:
                f.write(startup_script)
            
            os.chmod('start_bot.sh', 0o755)
            self.log_step("Startup Script", "SUCCESS", "start_bot.sh created")
            
            # Create systemd service file
            service_file = """[Unit]
Description=AutoFarming Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/my-1stproject
ExecStart=/root/my-1stproject/start_bot.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
            
            with open('autofarming-bot.service', 'w') as f:
                f.write(service_file)
            
            self.log_step("Systemd Service", "SUCCESS", "autofarming-bot.service created")
            
            return True
            
        except Exception as e:
            self.log_step("Startup Scripts", "FAILED", str(e))
            return False
    
    def create_monitoring_script(self):
        """Create monitoring and health check script."""
        logger.info("📊 Creating Monitoring Script...")
        
        try:
            monitoring_script = """#!/usr/bin/env python3
\"\"\"
AutoFarming Bot Health Monitor
Monitors bot health and performance
\"\"\"

import psutil
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_bot_process():
    \"\"\"Check if bot process is running.\"\"\"
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'python3' in proc.info['name'] and 'main.py' in ' '.join(proc.info['cmdline']):
                return True, proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False, None

def check_system_resources():
    \"\"\"Check system resource usage.\"\"\"
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        'cpu_percent': cpu_percent,
        'memory_percent': memory.percent,
        'disk_percent': disk.percent
    }

def main():
    \"\"\"Main monitoring function.\"\"\"
    logger.info("🔍 Starting AutoFarming Bot Health Monitor...")
    
    while True:
        try:
            # Check bot process
            bot_running, pid = check_bot_process()
            
            if bot_running:
                logger.info(f"✅ Bot running (PID: {pid})")
            else:
                logger.warning("⚠️ Bot not running")
            
            # Check system resources
            resources = check_system_resources()
            logger.info(f"📊 System: CPU {resources['cpu_percent']}%, "
                       f"Memory {resources['memory_percent']}%, "
                       f"Disk {resources['disk_percent']}%")
            
            time.sleep(60)  # Check every minute
            
        except KeyboardInterrupt:
            logger.info("🛑 Monitoring stopped")
            break
        except Exception as e:
            logger.error(f"❌ Monitoring error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
"""
            
            with open('monitor_bot.py', 'w') as f:
                f.write(monitoring_script)
            
            os.chmod('monitor_bot.py', 0o755)
            self.log_step("Monitoring Script", "SUCCESS", "monitor_bot.py created")
            
            return True
            
        except Exception as e:
            self.log_step("Monitoring Script", "FAILED", str(e))
            return False
    
    def generate_deployment_report(self):
        """Generate deployment report."""
        logger.info("📊 Generating Deployment Report...")
        
        total_steps = len(self.deployment_log)
        successful_steps = len([s for s in self.deployment_log if s['status'] == 'SUCCESS'])
        failed_steps = len([s for s in self.deployment_log if s['status'] == 'FAILED'])
        warning_steps = len([s for s in self.deployment_log if s['status'] == 'WARNING'])
        
        duration = datetime.now() - self.deployment_log[0]['timestamp'] if self.deployment_log else datetime.now()
        
        report = f"""# Production Deployment Report

**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Duration**: {duration.total_seconds():.2f} seconds

## Summary
- **Total Steps**: {total_steps}
- **Successful**: {successful_steps} ✅
- **Failed**: {failed_steps} ❌
- **Warnings**: {warning_steps} ⚠️
- **Success Rate**: {(successful_steps/total_steps*100):.1f}%

## Deployment Steps

"""
        
        for step in self.deployment_log:
            status_icon = "✅" if step['status'] == "SUCCESS" else "❌" if step['status'] == "FAILED" else "⚠️"
            report += f"- {status_icon} **{step['step']}**: {step['status']}\n"
            if step['details']:
                report += f"  - Details: {step['details']}\n"
        
        report += f"""

## Production Status

"""
        
        if failed_steps == 0:
            report += "- **✅ READY FOR PRODUCTION**: All deployment steps completed successfully\n"
        else:
            report += f"- **❌ DEPLOYMENT FAILED**: {failed_steps} critical issues need to be resolved\n"
        
        if warning_steps > 0:
            report += f"- **⚠️ WARNINGS**: {warning_steps} non-critical issues to address\n"
        
        report += f"""

## Next Steps

### If Deployment Successful:
1. **Start the bot**: `./start_bot.sh`
2. **Monitor health**: `python3 monitor_bot.py`
3. **Set up systemd**: `sudo cp autofarming-bot.service /etc/systemd/system/`
4. **Enable service**: `sudo systemctl enable autofarming-bot`
5. **Start service**: `sudo systemctl start autofarming-bot`

### If Deployment Failed:
1. Address all failed steps
2. Re-run deployment script
3. Verify environment configuration
4. Test bot startup manually

## Files Created
- `start_bot.sh` - Bot startup script
- `autofarming-bot.service` - Systemd service file
- `monitor_bot.py` - Health monitoring script
- `logs/` - Log directory structure
- `data/` - Data directory
- `backups/` - Backup directory

---
*Generated by Production Deployment Script*
"""
        
        # Save report
        with open('DEPLOYMENT_REPORT.md', 'w') as f:
            f.write(report)
        
        logger.info(f"✅ Deployment report generated: DEPLOYMENT_REPORT.md")
        logger.info(f"📊 Results: {successful_steps}/{total_steps} steps successful ({(successful_steps/total_steps*100):.1f}%)")
        
        return report
    
    def deploy(self):
        """Run complete deployment process."""
        logger.info("🚀 Starting Production Deployment...")
        logger.info("=" * 50)
        
        # Run all deployment steps
        steps = [
            ("Prerequisites Check", self.check_prerequisites),
            ("Environment Validation", self.validate_environment),
            ("Dependencies Test", self.test_dependencies),
            ("Production Structure", self.create_production_structure),
            ("Startup Scripts", self.create_startup_scripts),
            ("Monitoring Script", self.create_monitoring_script)
        ]
        
        all_successful = True
        
        for step_name, step_func in steps:
            try:
                if not step_func():
                    all_successful = False
                    break
            except Exception as e:
                self.log_step(step_name, "FAILED", str(e))
                all_successful = False
                break
        
        logger.info("=" * 50)
        logger.info("🏁 Production Deployment Complete!")
        
        if all_successful:
            logger.info("🎉 DEPLOYMENT SUCCESSFUL - Bot ready for production!")
        else:
            logger.error("❌ DEPLOYMENT FAILED - Check deployment report for details")
        
        return self.generate_deployment_report()

def main():
    """Main function to run the deployment."""
    deployment = ProductionDeployment()
    report = deployment.deploy()
    print("\n" + "=" * 50)
    print("📋 DEPLOYMENT SUMMARY")
    print("=" * 50)
    print(report)

if __name__ == "__main__":
    main() 