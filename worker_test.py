import asyncio
import os
from dotenv import load_dotenv
from telethon import TelegramClient

# Load environment variables from the config folder
load_dotenv('config/.env')

# Get credentials from .env file
API_ID = os.getenv("WORKER_API_ID")
API_HASH = os.getenv("WORKER_API_HASH")
# Get the username instead of the ID
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")

# Name for the session file that will be created
SESSION_NAME = "worker_session"

async def main():
    # Use 'with' to ensure the client is always disconnected
    async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        print("Worker client started...")

        # Send a test message to yourself (the admin) using the username
        await client.send_message(ADMIN_USERNAME, 'Hello from the worker account!')

        print("Test message sent successfully to the admin account.")
        print("You can now stop this script with Ctrl+C.")

if __name__ == "__main__":
    print("Attempting to log in as the worker account...")
    # Run the main asynchronous function
    asyncio.run(main())
