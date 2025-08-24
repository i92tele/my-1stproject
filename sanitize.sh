#!/bin/bash

# =============================================================================
# SANITIZE SCRIPT - Clean up ghost and zombie processes
# =============================================================================
# This script finds and kills all ghost and zombie processes that might
# interfere with the bot startup and operation.
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# =============================================================================
# SECTION 1: KILL BOT-RELATED PROCESSES
# =============================================================================

log "Starting sanitization process..."

info "Step 1: Killing bot-related processes..."

# Kill all Python processes related to the bot
BOT_PROCESSES=(
    "python3 bot.py"
    "python3 start_bot.py"
    "python3 scheduler.py"
    "python3 payment_monitor.py"
    "python3 -m scheduler"
    "python3 health_check.py"
    "python3 restart_recovery.py"
)

for process in "${BOT_PROCESSES[@]}"; do
    if pgrep -f "$process" > /dev/null; then
        log "Killing process: $process"
        pkill -f "$process" || true
        sleep 1
        # Force kill if still running
        pkill -9 -f "$process" || true
    else
        info "No process found: $process"
    fi
done

# =============================================================================
# SECTION 2: KILL ZOMBIE PROCESSES
# =============================================================================

info "Step 2: Finding and killing zombie processes..."

# Find zombie processes (defunct processes)
ZOMBIES=$(ps aux | grep -E "Z|defunct" | grep -v grep | awk '{print $2}' | tr '\n' ' ')

if [ -n "$ZOMBIES" ]; then
    warn "Found zombie processes: $ZOMBIES"
    for zombie in $ZOMBIES; do
        if [ -n "$zombie" ] && [ "$zombie" != "PID" ]; then
            log "Attempting to kill zombie process: $zombie"
            kill -9 "$zombie" 2>/dev/null || true
        fi
    done
else
    log "No zombie processes found"
fi

# =============================================================================
# SECTION 3: KILL ORPHANED PROCESSES
# =============================================================================

info "Step 3: Finding and killing orphaned processes..."

# Find processes with PPID 1 (orphaned)
ORPHANS=$(ps -eo pid,ppid,comm | awk '$2 == 1 && $3 ~ /python|node|java|ruby|php/ {print $1}' | tr '\n' ' ')

if [ -n "$ORPHANS" ]; then
    warn "Found orphaned processes: $ORPHANS"
    for orphan in $ORPHANS; do
        if [ -n "$orphan" ]; then
            log "Attempting to kill orphaned process: $orphan"
            kill -9 "$orphan" 2>/dev/null || true
        fi
    done
else
    log "No orphaned processes found"
fi

# =============================================================================
# SECTION 4: KILL GHOST PROCESSES (DEFUNCT)
# =============================================================================

info "Step 4: Finding and killing ghost/defunct processes..."

# Find defunct processes
DEFUNCT=$(ps aux | grep -E "defunct|Z" | grep -v grep | awk '{print $2}' | tr '\n' ' ')

if [ -n "$DEFUNCT" ]; then
    warn "Found defunct processes: $DEFUNCT"
    for defunct in $DEFUNCT; do
        if [ -n "$defunct" ] && [ "$defunct" != "PID" ]; then
            log "Attempting to kill defunct process: $defunct"
            kill -9 "$defunct" 2>/dev/null || true
        fi
    done
else
    log "No defunct processes found"
fi

# =============================================================================
# SECTION 5: KILL HANGING NETWORK PROCESSES
# =============================================================================

info "Step 5: Finding and killing hanging network processes..."

# Kill processes using common bot ports
BOT_PORTS=(8080 8443 3000 5000 8000 9000)

for port in "${BOT_PORTS[@]}"; do
    PID=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$PID" ]; then
        warn "Found process using port $port: $PID"
        log "Killing process on port $port"
        kill -9 "$PID" 2>/dev/null || true
    fi
done

# =============================================================================
# SECTION 6: KILL PYTHON PROCESSES WITH BOT-RELATED NAMES
# =============================================================================

info "Step 6: Killing Python processes with bot-related names..."

BOT_KEYWORDS=(
    "bot"
    "scheduler"
    "payment"
    "worker"
    "telegram"
    "auto"
    "farming"
    "posting"
)

for keyword in "${BOT_KEYWORDS[@]}"; do
    PIDS=$(pgrep -f "python.*$keyword" 2>/dev/null || true)
    if [ -n "$PIDS" ]; then
        warn "Found Python processes with keyword '$keyword': $PIDS"
        for pid in $PIDS; do
            log "Killing Python process with keyword '$keyword': $pid"
            kill -9 "$pid" 2>/dev/null || true
        done
    fi
done

# =============================================================================
# SECTION 7: CLEAN UP TEMPORARY FILES
# =============================================================================

info "Step 7: Cleaning up temporary files..."

# Remove lock files
LOCK_FILES=(
    "bot.lock"
    "scheduler.lock"
    "payment.lock"
    "worker.lock"
    "*.pid"
    "*.tmp"
)

for lock_file in "${LOCK_FILES[@]}"; do
    if ls $lock_file 2>/dev/null; then
        log "Removing lock file: $lock_file"
        rm -f $lock_file
    fi
done

# =============================================================================
# SECTION 8: CLEAN UP PYTHON CACHE
# =============================================================================

info "Step 8: Cleaning up Python cache files..."

# Remove Python cache directories
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true

# =============================================================================
# SECTION 9: FINAL CLEANUP
# =============================================================================

info "Step 9: Final cleanup..."

# Wait a moment for processes to terminate
sleep 2

# Check for any remaining bot processes
REMAINING=$(pgrep -f "python.*bot\|python.*scheduler\|python.*payment" 2>/dev/null || true)

if [ -n "$REMAINING" ]; then
    warn "Remaining bot-related processes found: $REMAINING"
    for pid in $REMAINING; do
        log "Force killing remaining process: $pid"
        kill -9 "$pid" 2>/dev/null || true
    done
else
    log "No remaining bot-related processes found"
fi

# =============================================================================
# SECTION 10: VERIFICATION
# =============================================================================

info "Step 10: Verification..."

# Check system status
log "System status after sanitization:"

# Check for zombie processes
ZOMBIE_COUNT=$(ps aux | grep -E "Z|defunct" | grep -v grep | wc -l)
log "Zombie processes remaining: $ZOMBIE_COUNT"

# Check for orphaned processes
ORPHAN_COUNT=$(ps -eo pid,ppid,comm | awk '$2 == 1 && $3 ~ /python|node|java|ruby|php/ {count++} END {print count+0}')
log "Orphaned processes remaining: $ORPHAN_COUNT"

# Check for bot processes
BOT_COUNT=$(pgrep -f "python.*bot\|python.*scheduler\|python.*payment" 2>/dev/null | wc -l)
log "Bot-related processes remaining: $BOT_COUNT"

# =============================================================================
# SECTION 11: SYSTEM RESOURCES
# =============================================================================

info "Step 11: System resource check..."

# Check memory usage
MEMORY_USAGE=$(free -h | grep Mem | awk '{print $3 "/" $2}')
log "Memory usage: $MEMORY_USAGE"

# Check disk usage
DISK_USAGE=$(df -h . | tail -1 | awk '{print $5}')
log "Disk usage: $DISK_USAGE"

# Check load average
LOAD_AVG=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}')
log "Load average: $LOAD_AVG"

# =============================================================================
# COMPLETION
# =============================================================================

log "Sanitization process completed successfully!"
log "System is now clean and ready for bot startup."

# Optional: Show a summary
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}           SANITIZATION SUMMARY        ${NC}"
echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}✓ Bot-related processes: Killed${NC}"
echo -e "${GREEN}✓ Zombie processes: Cleaned${NC}"
echo -e "${GREEN}✓ Orphaned processes: Removed${NC}"
echo -e "${GREEN}✓ Ghost processes: Eliminated${NC}"
echo -e "${GREEN}✓ Lock files: Removed${NC}"
echo -e "${GREEN}✓ Python cache: Cleaned${NC}"
echo -e "${GREEN}✓ System resources: Checked${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Exit successfully
exit 0
