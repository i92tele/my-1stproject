#!/bin/bash

# AutoFarming Bot Setup Script
# This script sets up the development environment for the AutoFarming Bot

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python_version() {
    print_status "Checking Python version..."
    
    if ! command_exists python3; then
        print_error "Python 3 is not installed. Please install Python 3.8 or higher."
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    print_success "Python $PYTHON_VERSION found"
    
    # Check if version is 3.8 or higher
    MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 8 ]); then
        print_error "Python 3.8 or higher is required. Current version: $PYTHON_VERSION"
        exit 1
    fi
}

# Function to create virtual environment
create_venv() {
    print_status "Setting up virtual environment..."
    
    if [ -d "venv" ]; then
        print_warning "Virtual environment 'venv' already exists"
        read -p "Do you want to recreate it? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_status "Removing existing virtual environment..."
            rm -rf venv
        else
            print_status "Using existing virtual environment"
            return 0
        fi
    fi
    
    print_status "Creating virtual environment..."
    python3 -m venv venv
    
    if [ ! -d "venv" ]; then
        print_error "Failed to create virtual environment"
        exit 1
    fi
    
    print_success "Virtual environment created successfully"
}

# Function to activate virtual environment
activate_venv() {
    print_status "Activating virtual environment..."
    
    if [ ! -d "venv" ]; then
        print_error "Virtual environment not found. Run setup again."
        exit 1
    fi
    
    # Source the virtual environment
    source venv/bin/activate
    
    # Verify activation
    if [ -z "$VIRTUAL_ENV" ]; then
        print_error "Failed to activate virtual environment"
        exit 1
    fi
    
    print_success "Virtual environment activated: $VIRTUAL_ENV"
}

# Function to upgrade pip
upgrade_pip() {
    print_status "Upgrading pip..."
    # Use the virtual environment's pip explicitly
    venv/bin/pip install --upgrade pip
    print_success "Pip upgraded successfully"
}

# Function to install requirements
install_requirements() {
    print_status "Installing requirements..."
    
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt not found"
        exit 1
    fi
    
    # Install requirements using virtual environment's pip
    venv/bin/pip install -r requirements.txt
    
    if [ $? -eq 0 ]; then
        print_success "Requirements installed successfully"
    else
        print_error "Failed to install requirements"
        exit 1
    fi
}

# Function to verify installation
verify_installation() {
    print_status "Verifying installation..."
    
    # List of critical packages to check
    CRITICAL_PACKAGES=(
        "telegram"
        "dotenv"
        "aiohttp"
        "asyncpg"
    )
    
    MISSING_PACKAGES=()
    
    for package in "${CRITICAL_PACKAGES[@]}"; do
        if ! venv/bin/python3 -c "import $package" 2>/dev/null; then
            MISSING_PACKAGES+=("$package")
        fi
    done
    
    if [ ${#MISSING_PACKAGES[@]} -eq 0 ]; then
        print_success "All critical packages installed correctly"
    else
        print_error "Missing packages: ${MISSING_PACKAGES[*]}"
        print_status "Attempting to install missing packages..."
        venv/bin/pip install "${MISSING_PACKAGES[@]}"
    fi
}

# Function to test imports
test_imports() {
    print_status "Testing critical imports..."
    
    # Test basic imports using virtual environment's Python
    venv/bin/python3 -c "
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath('.')))

try:
    import config
    print('✅ config module imported successfully')
except ImportError as e:
    print(f'❌ Failed to import config: {e}')
    sys.exit(1)

try:
    import database
    print('✅ database module imported successfully')
except ImportError as e:
    print(f'❌ Failed to import database: {e}')
    sys.exit(1)

try:
    from commands import user_commands, admin_commands
    print('✅ commands modules imported successfully')
except ImportError as e:
    print(f'❌ Failed to import commands: {e}')
    sys.exit(1)

print('✅ All critical imports successful')
"
    
    if [ $? -eq 0 ]; then
        print_success "All critical imports working correctly"
    else
        print_error "Some imports failed. Check your code for syntax errors."
        exit 1
    fi
}

# Function to create activation script
create_activation_script() {
    print_status "Creating activation helper script..."
    
    cat > activate_env.sh << 'EOF'
#!/bin/bash
# AutoFarming Bot Environment Activation Script

if [ -d "venv" ]; then
    echo "Activating AutoFarming Bot virtual environment..."
    source venv/bin/activate
    echo "✅ Virtual environment activated!"
    echo "📝 To deactivate, run: deactivate"
    echo "🚀 To run the bot, use: python3 bot.py"
    echo "🏥 To run health checks, use: python3 quick_health_check.py"
else
    echo "❌ Virtual environment not found. Run setup.sh first."
    exit 1
fi
EOF
    
    chmod +x activate_env.sh
    print_success "Activation script created: activate_env.sh"
}

# Function to display setup completion message
show_completion_message() {
    echo
    echo "🎉 SETUP COMPLETED SUCCESSFULLY!"
    echo "=================================="
    echo
    echo "📋 NEXT STEPS:"
    echo "1. Activate the environment:"
    echo "   source venv/bin/activate"
    echo "   # OR use the helper script:"
    echo "   ./activate_env.sh"
    echo
    echo "2. Run health checks:"
    echo "   python3 quick_health_check.py"
    echo "   python3 health_check.py"
    echo
    echo "3. Start the bot:"
    echo "   python3 bot.py"
    echo
    echo "📝 USEFUL COMMANDS:"
    echo "   source venv/bin/activate    # Activate environment"
    echo "   deactivate                  # Deactivate environment"
    echo "   pip list                    # List installed packages"
    echo "   python3 quick_health_check.py  # Quick health check"
    echo "   python3 health_check.py        # Full health check"
    echo
    echo "🔧 TROUBLESHOOTING:"
    echo "   - If you get import errors, make sure you're in the project root"
    echo "   - If packages are missing, run: pip install -r requirements.txt"
    echo "   - If virtual environment is corrupted, delete 'venv' and run setup.sh again"
    echo
    echo "📁 PROJECT STRUCTURE:"
    echo "   venv/                      # Virtual environment"
    echo "   bot.py                     # Main bot file"
    echo "   config.py                  # Configuration"
    echo "   database.py                # Database manager"
    echo "   requirements.txt            # Dependencies"
    echo "   quick_health_check.py      # Quick health check"
    echo "   health_check.py            # Full health check"
    echo "   activate_env.sh            # Environment activation helper"
    echo
}

# Function to check for .env file
check_env_file() {
    print_status "Checking for environment configuration..."
    
    if [ ! -f "config/.env" ]; then
        print_warning "config/.env file not found"
        echo
        echo "📝 ENVIRONMENT SETUP REQUIRED:"
        echo "Create config/.env file with the following variables:"
        echo
        echo "BOT_TOKEN=your_bot_token_from_botfather"
        echo "ADMIN_ID=your_telegram_user_id"
        echo "DATABASE_URL=postgresql://user:password@localhost/dbname"
        echo
        echo "Optional variables:"
        echo "BTC_ADDRESS=your_btc_address"
        echo "ETH_ADDRESS=your_eth_address"
        echo "TON_ADDRESS=your_ton_address"
        echo
        echo "💡 You can copy from config/env_template.txt if it exists"
    else
        print_success "config/.env file found"
    fi
}

# Main setup function
main() {
    echo "🚀 AutoFarming Bot Setup Script"
    echo "================================"
    echo
    
    # Check if we're in the right directory
    if [ ! -f "bot.py" ]; then
        print_error "bot.py not found. Please run this script from the project root directory."
        exit 1
    fi
    
    # Run setup steps
    check_python_version
    create_venv
    activate_venv
    upgrade_pip
    install_requirements
    verify_installation
    test_imports
    create_activation_script
    check_env_file
    show_completion_message
    
    print_success "Setup completed successfully!"
}

# Run main function
main "$@" 