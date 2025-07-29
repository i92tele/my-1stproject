import asyncio
import os
from dotenv import load_dotenv
from telethon import TelegramClient
import logging

# Import your existing database and config classes
from database import DatabaseManager
from config import BotConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from the config folder
load_dotenv('config/.env')

# Get worker credentials from .env file
API_ID = os.getenv("WORKER_API_ID")
API_HASH = os.getenv("WORKER_API_HASH")
SESSION_NAME = "worker_session"

async def main():
    # Initialize config and database
    config = BotConfig.load_from_env()
    db = DatabaseManager(config, logger)
    await db.initialize()
    
    logger.info("Scheduler started. Connecting worker account...")

    # Connect the Telethon client for the worker account
    worker_client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    
    async with worker_client:
        logger.info("Worker account connected successfully.")
        
        # This is the main scheduler loop
        while True:
            try:
                logger.info("Scheduler checking for due ads...")
                due_ads = await db.get_due_ads()
                
                if not due_ads:
                    logger.info("No ads are due.")
                else:
                    logger.info(f"Found {len(due_ads)} ad(s) to send.")

                for ad in due_ads:
                    user_id = ad['user_id']
                    ad_id = ad['id']
                    
                    destinations = await db.get_destinations(user_id)
                    if not destinations:
                        logger.warning(f"User {user_id} has a due ad but no destinations. Skipping.")
                        await db.update_ad_last_sent(ad_id)
                        continue
                        
                    message_content = ad['message_text']
                    
                    logger.info(f"Processing ad {ad_id} for user {user_id} to {len(destinations)} destinations.")
                    
                    for dest in destinations:
                        try:
                            # Use 'await client.get_input_entity' for robustness
                            dest_entity = await worker_client.get_input_entity(int(dest['destination_id']))
                            await worker_client.send_message(dest_entity, message_content)
                            logger.info(f"Sent message to destination {dest['destination_id']}")
                            # Anti-spam delay
                            await asyncio.sleep(30)
                        except Exception as e:
                            logger.error(f"Failed to send to destination {dest['destination_id']}: {e}")
                    
                    await db.update_ad_last_sent(ad_id)
                    logger.info(f"Finished processing ad {ad_id} for user {user_id}.")

            except Exception as e:
                logger.error(f"An error occurred in the main scheduler loop: {e}")

            # Wait for the next check cycle
            await asyncio.sleep(60)

    await db.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Scheduler stopped manually.")
