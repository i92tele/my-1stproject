#!/usr/bin/env python3
import asyncio
import os
from dotenv import load_dotenv
from telegram.ext import Application, ApplicationBuilder, CommandHandler

load_dotenv('config/.env')

async def start(update, context):
    await update.message.reply_text("Fresh bot is working!")

async def main():
    token = os.getenv('BOT_TOKEN')
    print(f"Starting fresh bot with token: {token[:20]}...")
    
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    
    print("Bot starting...")
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
