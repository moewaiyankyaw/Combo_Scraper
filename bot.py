import os
import re
import random
import asyncio
import logging
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaDocument
from telethon.sessions import StringSession

# Configuration
BOT_TOKEN = '8479206171:AAF8Jc5dvQ-KfMPgM9cjwLP3oG0hwyUZYTQ'
API_ID = 29464258
API_HASH = '5ca1ad6d6e0aa144a6e407e0af64510f'
SESSION_FILES = {
    'bot': 'bot.session',
    'user': 'user.session'
}

# Target channels grouped into three groups
CHANNEL_GROUPS = [
    # Group 1
    [
        'https://t.me/+E5x65zAb-GphNjlk',
        'https://t.me/+_7HlFcVVpyYwMjIx',
        'https://t.me/+U9YOffLRn5JjYjYy'
    ],
    # Group 2
    [
        'https://t.me/freedatabasegroupp',
        'https://t.me/voscall_cloud',
        'https://t.me/BrowzDataCloud'
    ],
    # Group 3
    [
        'https://t.me/combospublic123',
        'https://t.me/+wE9VErPqOPgyMWFk',
        'http://t.me/+QOWpGkEz6eVlZTQ1'
    ]
]

# Regex patterns
EMAIL_PASS_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}:[^\s]+$')
PROXY_PATTERN = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$')

async def initialize_client(client_type):
    """Initialize Telegram client with persistent session"""
    if client_type == 'bot':
        client = TelegramClient(SESSION_FILES['bot'], API_ID, API_HASH)
        await client.start(bot_token=BOT_TOKEN)
        return client
    
    # User client with StringSession persistence
    if os.path.exists(SESSION_FILES['user']):
        with open(SESSION_FILES['user'], 'r') as f:
            session_str = f.read().strip()
        client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    else:
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.start()
        with open(SESSION_FILES['user'], 'w') as f:
            f.write(client.session.save())
    
    return client

async def scrape_files_from_group(client, target_channels, target_date):
    """Scrape and process files from a specific group of channels"""
    all_lines = set()
    next_day = target_date + timedelta(days=1)
    downloaded_files = []  # Store all downloaded file paths
    
    for channel in target_channels:
        try:
            # Check if client is still connected
            if not client.is_connected():
                await client.connect()
                
            entity = await client.get_entity(channel)
            async for message in client.iter_messages(
                entity,
                offset_date=target_date,
                reverse=True
            ):
                if message.date.date() >= next_day:
                    break
                if (message.date.date() == target_date and 
                    message.media and 
                    isinstance(message.media, MessageMediaDocument)):
                    
                    doc = message.media.document
                    is_text_file = (
                        doc.mime_type == 'text/plain' or 
                        (
                            hasattr(doc, 'attributes') and 
                            doc.attributes and 
                            hasattr(doc.attributes[0], 'file_name') and 
                            doc.attributes[0].file_name.lower().endswith('.txt')
                        )
                    )
                    
                    if is_text_file:
                        try:
                            file_path = await client.download_media(message)
                            if file_path:
                                downloaded_files.append(file_path)  # Save the file path
                                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    for line in f:
                                        line = line.strip()
                                        if (
                                            line and 
                                            not PROXY_PATTERN.match(line) and 
                                            EMAIL_PASS_PATTERN.match(line)
                                        ):
                                            all_lines.add(line)
                        except Exception as e:
                            print(f"Error processing file: {e}")
                            continue
        except Exception as e:
            print(f"Error scraping {channel}: {e}")
            continue
    
    # Cleanup: Delete all downloaded files after processing
    for file_path in downloaded_files:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")
    
    return list(all_lines)

async def scrape_files(client, target_date):
    """Scrape files from all channel groups one by one"""
    all_lines = set()
    
    for i, channel_group in enumerate(CHANNEL_GROUPS, 1):
        print(f"Processing channel group {i}...")
        try:
            group_lines = await scrape_files_from_group(client, channel_group, target_date)
            all_lines.update(group_lines)
            print(f"Found {len(group_lines)} combos in group {i}")
        except Exception as e:
            print(f"Error processing group {i}: {e}")
            continue
    
    return list(all_lines)

async def send_results(bot_client, user_id, lines):
    """Send processed results to user"""
    if not lines:
        await bot_client.send_message(user_id, "❌ No valid combos found for the specified date.")
        return
    
    random.shuffle(lines)
    chunk_size = random.randint(50000, 70000)
    
    for i, chunk in enumerate([lines[i:i + chunk_size] for i in range(0, len(lines), chunk_size)], 1):
        filename = f"combos_{i}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(chunk))
        
        await bot_client.send_file(
            user_id,
            filename,
            caption=f"📅 Part {i} | 📝 {len(chunk):,} lines\n🔄 Mixed & Deduplicated"
        )
        # Delete the temporary combo file after sending
        try:
            os.remove(filename)
        except Exception as e:
            print(f"Error deleting combo file {filename}: {e}")

async def setup_bot_handlers(bot_client, user_client):
    """Configure bot command handlers"""
    @bot_client.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        await event.reply("""🤖 **Combo Scraper Bot**\n\n"""
                        """Send a date in DD.MM.YYYY format to scrape combos from that day.\n"""
                        """Example: `09.08.2025`""")

    @bot_client.on(events.NewMessage())
    async def message_handler(event):
        try:
            input_date = datetime.strptime(event.text, '%d.%m.%Y').date()
            if input_date > datetime.now().date():
                await event.reply("❌ Future dates not allowed. Enter a past date.")
                return
        except ValueError:
            if not event.text.startswith('/'):
                await event.reply("❌ Invalid format. Use DD.MM.YYYY")
            return

        msg = await event.reply(f"🔍 Searching for {input_date.strftime('%d.%m.%Y')}...")
        
        try:
            # Ensure user client is connected
            if not user_client.is_connected():
                await user_client.connect()
                
            lines = await scrape_files(user_client, input_date)
            if not lines:
                await msg.edit("❌ No valid combos found for this date.")
                return
            
            await msg.edit(f"✅ Found {len(lines):,} combos\n📤 Preparing files...")
            await send_results(bot_client, event.chat_id, lines)
            await msg.edit(f"🎉 Done! Sent {len(lines):,} combos")
        except Exception as e:
            await msg.edit(f"❌ Error: {str(e)}")

async def main():
    """Main application entry point"""
    # Initialize clients
    bot_client = await initialize_client('bot')
    user_client = await initialize_client('user')
    
    # Setup bot handlers
    await setup_bot_handlers(bot_client, user_client)
    
    print("Bot is running and ready to accept requests...")
    await bot_client.run_until_disconnected()
    
    # Cleanup
    await user_client.disconnect()

if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(level=logging.WARNING)
    
    # Run application
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    finally:
        loop.close()
