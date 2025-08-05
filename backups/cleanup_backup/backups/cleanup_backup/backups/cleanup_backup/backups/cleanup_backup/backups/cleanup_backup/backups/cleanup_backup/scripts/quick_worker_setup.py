#!/usr/bin/env python3
"""
Quick Worker Setup - Batch Configuration
"""

import os
from dotenv import load_dotenv

def add_workers_to_env():
    """Add worker configurations to .env file."""
    
    # Your worker phone numbers (add more as needed)
    worker_phones = [
        "+447386300812",
        "+13018746514", 
        "+12534997118",
        "+573235112918",
        "+13015392356",
        "+3015177101",
        "+5307729",
        # Add more phone numbers here
    ]
    
    # Test API credentials (you can replace these later with your own)
    api_id = "2040"
    api_hash = "b18441a1ff607e10a989891a5462e627"
    
    # Load current .env
    load_dotenv('config/.env')
    
    # Read current .env content
    try:
        with open('config/.env', 'r') as f:
            env_content = f.read()
    except FileNotFoundError:
        env_content = ""
    
    # Add worker configurations
    worker_config = "\n# Worker Account Credentials\n"
    
    for i, phone in enumerate(worker_phones, 1):
        worker_config += f"\n# Worker {i}\n"
        worker_config += f"WORKER_{i}_API_ID={api_id}\n"
        worker_config += f"WORKER_{i}_API_HASH={api_hash}\n"
        worker_config += f"WORKER_{i}_PHONE={phone}\n"
    
    # Add to .env file
    with open('config/.env', 'a') as f:
        f.write(worker_config)
    
    print(f"✅ Added {len(worker_phones)} workers to config/.env")
    print(f"📱 Workers: {', '.join(worker_phones)}")
    print(f"🔑 Using test API credentials (you can replace these later)")
    
    return len(worker_phones)

def test_worker_config():
    """Test the worker configuration."""
    print("\n🧪 Testing worker configuration...")
    
    # Check if .env has worker entries
    try:
        with open('config/.env', 'r') as f:
            content = f.read()
        
        worker_count = content.count('WORKER_')
        print(f"✅ Found {worker_count} worker configurations in .env")
        
        # Show first few workers
        lines = content.split('\n')
        worker_lines = [line for line in lines if line.startswith('WORKER_')]
        
        print("\n📋 Worker Configuration:")
        for i in range(0, min(12, len(worker_lines)), 4):
            if i + 3 < len(worker_lines):
                print(f"  Worker {i//4 + 1}: {worker_lines[i+2].split('=')[1]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing configuration: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Quick Worker Setup")
    print("=" * 40)
    
    # Add workers to .env
    worker_count = add_workers_to_env()
    
    # Test configuration
    test_worker_config()
    
    print(f"\n✅ Setup complete! Added {worker_count} workers.")
    print("\n📝 Next steps:")
    print("1. Run: python3 add_workers.py")
    print("2. Test the workers")
    print("3. Update scheduler.py to use multiple workers") 