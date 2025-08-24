# Add Flask web server for Render compatibility
from flask import Flask
import threading
import os
import io
import time

# Initialize Flask app
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Telegram Combo Scraper Bot is running", 200

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    # Use the PORT environment variable provided by Render
    port = int(os.environ.get("PORT", 10000))
    host = '0.0.0.0'  # Bind to all interfaces
    print(f"Starting Flask server on {host}:{port}")
    app.run(host=host, port=port, debug=False, use_reloader=False)

# Rest of your Telegram bot code
import re
import random
import asyncio
import logging
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaDocument
from telethon.sessions import StringSession

# Configuration - use environment variables for security
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8479206171:AAF8Jc5dvQ-KfMPgM9cjwLP3oG0hwyUZYTQ')
API_ID = int(os.environ.get('API_ID', 29464258))
API_HASH = os.environ.get('API_HASH', '5ca1ad6d6e0aa144a6e407e0af64510f')
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
        'https://t.me/+CVyvhBgtDfI1YzRi',
        'https://t.me/+wE9VErPqOPgyMWFk',
        'http://t.me/+QOWpGkEz6eVlZTQ1'
    ],
    # Group 4
    [
        'https://t.me/DuffyData',
        'https://t.me/+tvRxredx2i0zMTgy',
        'https://t.me/kingofcracking2'
    ],
    # Group 5
    [
        'https://t.me/+4TnRrTK881g1Y2Ri',
        'https://t.me/ninjapubliccloud',
        'https://t.me/combolistmailsgold'
    ]
]

# Regex patterns
EMAIL_PASS_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}:[^\s]+$')
PROXY_PATTERN = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Multiple test file options with timeouts
TEST_FILE_OPTIONS = [
    "https://httpbin.org/bytes/1024",  # 1KB test file
    "https://httpbin.org/bytes/512",   # 512B test file
    "https://httpbin.org/bytes/256",   # 256B test file
]

async def test_download_speed():
    """Test download speed by downloading a small test file with timeout"""
    import aiohttp
    import math
    
    logger.info("Starting download speed test...")
    
    # Try each test file until one works
    for test_url in TEST_FILE_OPTIONS:
        try:
            start_time = time.time()
            
            # Set timeout for the download
            timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(test_url) as response:
                    if response.status == 200:
                        content = await response.read()
                        end_time = time.time()
                        
                        download_time = end_time - start_time
                        file_size = len(content)
                        
                        # Calculate speed in different units
                        speed_bps = file_size / download_time
                        speed_kbps = speed_bps / 1024
                        speed_mbps = speed_kbps / 1024
                        
                        logger.info(f"Download test completed: {file_size} bytes in {download_time:.3f}s")
                        
                        return {
                            "success": True,
                            "file_size": file_size,
                            "download_time": download_time,
                            "speed_bps": speed_bps,
                            "speed_kbps": speed_kbps,
                            "speed_mbps": speed_mbps,
                            "ping_ms": download_time * 1000,
                            "test_url": test_url
                        }
                    else:
                        logger.warning(f"Download test failed with status: {response.status}, trying next URL")
                        continue
                        
        except asyncio.TimeoutError:
            logger.warning(f"Download test timed out for {test_url}, trying next URL")
            continue
        except Exception as e:
            logger.warning(f"Download test error for {test_url}: {e}, trying next URL")
            continue
    
    # If all test URLs failed, try a fallback method
    logger.warning("All download tests failed, using fallback method")
    try:
        # Simple fallback - just measure response time to a DNS query
        import socket
        start_time = time.time()
        socket.gethostbyname('google.com')
        ping_time = (time.time() - start_time) * 1000
        
        return {
            "success": True,
            "file_size": 0,
            "download_time": ping_time / 1000,
            "speed_bps": 0,
            "speed_kbps": 0,
            "speed_mbps": 0,
            "ping_ms": ping_time,
            "fallback": True,
            "message": "Used fallback DNS test"
        }
    except Exception as e:
        logger.error(f"Fallback test also failed: {e}")
        return {"success": False, "error": "All download tests failed"}

async def initialize_client(client_type):
    """Initialize Telegram client with persistent session"""
    logger.info(f"Initializing {client_type} client...")
    if client_type == 'bot':
        client = TelegramClient(SESSION_FILES['bot'], API_ID, API_HASH)
        await client.start(bot_token=BOT_TOKEN)
        logger.info("Bot client initialized successfully")
        return client
    
    # User client with StringSession persistence
    if os.path.exists(SESSION_FILES['user']):
        with open(SESSION_FILES['user'], 'r') as f:
            session_str = f.read().strip()
        client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
        logger.info("User client loaded from existing session")
    else:
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.start()
        with open(SESSION_FILES['user'], 'w') as f:
            f.write(client.session.save())
        logger.info("New user client session created and saved")
    
    return client

async def scrape_files_from_group(client, target_channels, target_date):
    """Scrape and process files from a specific group of channels - entirely in memory"""
    all_lines = set()
    next_day = target_date + timedelta(days=1)
    files_processed = 0
    valid_lines_found = 0
    
    for channel_idx, channel in enumerate(target_channels, 1):
        try:
            logger.info(f"Processing channel {channel_idx}/{len(target_channels)}: {channel}")
            
            # Check if client is still connected
            if not client.is_connected():
                logger.info("Client disconnected, reconnecting...")
                await client.connect()
                
            entity = await client.get_entity(channel)
            logger.info(f"Connected to channel: {channel}")
            
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
                        files_processed += 1
                        file_name = getattr(doc.attributes[0], 'file_name', 'unknown.txt')
                        file_size = doc.size
                        
                        logger.info(f"Downloading file: {file_name} ({file_size} bytes)")
                        download_start = time.time()
                        
                        try:
                            # Download file content directly to memory
                            file_bytes = await client.download_media(message, bytes)
                            download_time = time.time() - download_start
                            
                            if file_bytes:
                                logger.info(f"Downloaded {len(file_bytes)} bytes in {download_time:.2f}s, processing content...")
                                
                                # Process the file content directly from memory
                                file_text = file_bytes.decode('utf-8', errors='ignore')
                                lines = file_text.splitlines()
                                
                                logger.info(f"File contains {len(lines)} lines, filtering valid combos...")
                                
                                for line in lines:
                                    line = line.strip()
                                    if (
                                        line and 
                                        not PROXY_PATTERN.match(line) and 
                                        EMAIL_PASS_PATTERN.match(line)
                                    ):
                                        all_lines.add(line)
                                        valid_lines_found += 1
                                
                                logger.info(f"Processed file: {file_name} - Found {valid_lines_found} valid combos so far")
                                        
                        except Exception as e:
                            logger.error(f"Error processing file {file_name}: {e}")
                            continue
            
            logger.info(f"Finished processing channel {channel}, found {valid_lines_found} valid combos total")
            
        except Exception as e:
            logger.error(f"Error scraping {channel}: {e}")
            continue
    
    logger.info(f"Group processing complete: Processed {files_processed} files, found {len(all_lines)} unique combos")
    return list(all_lines)

async def scrape_files(client, target_date):
    """Scrape files from all channel groups one by one"""
    all_lines = set()
    total_start_time = time.time()
    
    logger.info(f"Starting scraping process for date: {target_date}")
    
    for i, channel_group in enumerate(CHANNEL_GROUPS, 1):
        group_start_time = time.time()
        logger.info(f"Processing channel group {i}/{len(CHANNEL_GROUPS)} with {len(channel_group)} channels")
        
        try:
            group_lines = await scrape_files_from_group(client, channel_group, target_date)
            all_lines.update(group_lines)
            
            group_time = time.time() - group_start_time
            logger.info(f"Completed group {i} in {group_time:.2f}s - Found {len(group_lines)} combos in this group")
            
        except Exception as e:
            logger.error(f"Error processing group {i}: {e}")
            continue
    
    total_time = time.time() - total_start_time
    logger.info(f"Scraping completed in {total_time:.2f}s - Total unique combos found: {len(all_lines)}")
    
    return list(all_lines)

async def send_results(bot_client, user_id, lines):
    """Send processed results to user - entirely in memory"""
    if not lines:
        logger.warning("No valid combos found to send")
        await bot_client.send_message(user_id, "❌ No valid combos found for the specified date.")
        return
    
    logger.info(f"Preparing to send {len(lines)} combos to user")
    
    random.shuffle(lines)
    chunk_size = random.randint(100000, 200000)
    chunks = [lines[i:i + chunk_size] for i in range(0, len(lines), chunk_size)]
    
    logger.info(f"Split into {len(chunks)} chunks for sending")
    
    for i, chunk in enumerate(chunks, 1):
        send_start = time.time()
        logger.info(f"Preparing chunk {i}/{len(chunks)} with {len(chunk)} combos")
        
        # Create file in memory
        file_content = '\n'.join(chunk)
        file_bytes = file_content.encode('utf-8')
        file_io = io.BytesIO(file_bytes)
        file_io.name = f"combos_{i}_By_@M69431(PVT).txt"
        
        logger.info(f"Sending chunk {i} ({len(file_bytes)} bytes)...")
        
        try:
            await bot_client.send_file(
                user_id,
                file_io,
                caption=f"📅 Part {i}/{len(chunks)} | 📝 {len(chunk):,} lines\n🔄 Mixed & Deduplicated"
            )
            
            send_time = time.time() - send_start
            logger.info(f"Successfully sent chunk {i} in {send_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Error sending chunk {i}: {e}")
            # Try to send an error message
            try:
                await bot_client.send_message(
                    user_id,
                    f"❌ Error sending part {i}: {str(e)}"
                )
            except:
                pass
    
    logger.info(f"Finished sending all {len(chunks)} chunks to user")

async def setup_bot_handlers(bot_client, user_client):
    """Configure bot command handlers"""
    @bot_client.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        logger.info(f"Received /start command from user {event.sender_id}")
        await event.reply("""🤖 **Combo Scraper Bot**\n\n"""
                        """Send a date in DD.MM.YYYY format to scrape combos from that day.\n"""
                        """Example: `09.08.2025`\n\n"""
                        """Use /ping to test bot response time and download speed""")

    @bot_client.on(events.NewMessage(pattern='/ping'))
    async def ping_handler(event):
        logger.info(f"Received /ping command from user {event.sender_id}")
        
        # Send initial response
        msg = await event.reply("🏓 Pong! Testing connection...")
        
        # Test 1: Bot response time
        bot_response_start = time.time()
        await msg.edit("🏓 Testing bot response time...")
        bot_response_time = (time.time() - bot_response_start) * 1000  # Convert to ms
        
        # Test 2: Download speed test with timeout
        await msg.edit("🌐 Testing download speed (max 15s)...")
        
        # Run download test with a timeout to prevent hanging
        try:
            speed_test_task = asyncio.create_task(test_download_speed())
            speed_test_result = await asyncio.wait_for(speed_test_task, timeout=15.0)
        except asyncio.TimeoutError:
            speed_test_result = {"success": False, "error": "Download test timed out after 15 seconds"}
            logger.error("Download test timed out")
        except Exception as e:
            speed_test_result = {"success": False, "error": f"Download test error: {str(e)}"}
            logger.error(f"Download test failed: {e}")
        
        # Format the results
        if speed_test_result["success"]:
            if speed_test_result.get("fallback", False):
                response_message = (
                    f"✅ **Bot Status Report**\n\n"
                    f"🤖 **Bot Response Time**: {bot_response_time:.2f} ms\n"
                    f"📡 **Network Latency**: {speed_test_result['ping_ms']:.2f} ms\n"
                    f"ℹ️ **Note**: {speed_test_result.get('message', 'Used fallback test')}\n\n"
                    f"🟢 **Status**: Online and responsive"
                )
            else:
                response_message = (
                    f"✅ **Bot Status Report**\n\n"
                    f"🤖 **Bot Response Time**: {bot_response_time:.2f} ms\n"
                    f"🌐 **Download Speed**: {speed_test_result['speed_mbps']:.2f} Mbps\n"
                    f"📊 **Download Test**: {speed_test_result['file_size']} bytes in {speed_test_result['download_time']:.3f}s\n"
                    f"📡 **Ping Time**: {speed_test_result['ping_ms']:.2f} ms\n\n"
                    f"🟢 **Status**: Online and responsive"
                )
        else:
            response_message = (
                f"⚠️ **Bot Status Report**\n\n"
                f"🤖 **Bot Response Time**: {bot_response_time:.2f} ms\n"
                f"❌ **Download Test Failed**: {speed_test_result.get('error', 'Unknown error')}\n\n"
                f"🟡 **Status**: Online but download test failed"
            )
        
        await msg.edit(response_message)
        logger.info(f"Ping test completed for user {event.sender_id}")

    @bot_client.on(events.NewMessage())
    async def message_handler(event):
        # Ignore commands other than /start and /ping
        if event.text.startswith('/') and event.text not in ['/start', '/ping']:
            return
            
        logger.info(f"Received message from user {event.sender_id}: {event.text}")
        
        try:
            input_date = datetime.strptime(event.text, '%d.%m.%Y').date()
            if input_date > datetime.now().date():
                logger.warning(f"User {event.sender_id} requested future date: {input_date}")
                await event.reply("❌ Future dates not allowed. Enter a past date.")
                return
        except ValueError:
            if not event.text.startswith('/'):
                logger.warning(f"User {event.sender_id} sent invalid date format: {event.text}")
                await event.reply("❌ Invalid format. Use DD.MM.YYYY")
            return

        logger.info(f"User {event.sender_id} requested scraping for date: {input_date}")
        msg = await event.reply(f"🔍 Searching for {input_date.strftime('%d.%m.%Y')}...")
        
        try:
            # Ensure user client is connected
            if not user_client.is_connected():
                logger.info("User client disconnected, reconnecting...")
                await user_client.connect()
                
            lines = await scrape_files(user_client, input_date)
            if not lines:
                logger.info(f"No combos found for date {input_date}")
                await msg.edit("❌ No valid combos found for this date.")
                return
            
            logger.info(f"Found {len(lines)} combos, preparing to send to user {event.sender_id}")
            await msg.edit(f"✅ Found {len(lines):,} combos\n📤 Preparing files...")
            
            await send_results(bot_client, event.chat_id, lines)
            
            logger.info(f"Successfully sent all files to user {event.sender_id}")
            await msg.edit(f"🎉 Done! Sent {len(lines):,} combos")
            
        except Exception as e:
            logger.error(f"Error processing request from user {event.sender_id}: {e}")
            await msg.edit(f"❌ Error: {str(e)}")

async def main():
    """Main application entry point"""
    logger.info("Starting Telegram Combo Scraper Bot...")
    
    # Initialize clients
    bot_client = await initialize_client('bot')
    user_client = await initialize_client('user')
    
    # Setup bot handlers
    await setup_bot_handlers(bot_client, user_client)
    
    logger.info("Bot is running and ready to accept requests...")
    await bot_client.run_until_disconnected()
    
    # Cleanup
    await user_client.disconnect()
    logger.info("Bot stopped")

if __name__ == '__main__':
    # Get the port from Render's environment variable
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"Render provided PORT: {port}")
    
    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info(f"Flask server started on port {port}")
    
    # Run application
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        loop.close()
