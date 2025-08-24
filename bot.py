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
        'https://t.me/combospublic123',
        'https://t.me/+wE9VErPqOPgyMWFk',
        'http://t.me/+QOWpGkEz6eVlZTQ1'
    ]
]

# Regex patterns
EMAIL_PASS_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}:[^\s]+$')
PROXY_PATTERN = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$')

# Disable all logging
logging.disable(logging.CRITICAL)

# Multiple test file options with timeouts
TEST_FILE_OPTIONS = [
    "https://httpbin.org/bytes/1024",  # 1KB test file
    "https://httpbin.org/bytes/512",   # 512B test file
    "https://httpbin.org/bytes/256",   # 256B test file
]

async def test_download_speed():
    """Test download speed by downloading a small test file with timeout"""
    import aiohttp
    
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
                        continue
                        
        except asyncio.TimeoutError:
            continue
        except Exception:
            continue
    
    # If all test URLs failed, try a fallback method
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
    except Exception:
        return {"success": False, "error": "All download tests failed"}

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
    """Scrape and process files from a specific group of channels - entirely in memory"""
    all_lines = set()
    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = datetime.combine(target_date, datetime.max.time())
    
    for channel in target_channels:
        try:
            # Check if client is still connected
            if not client.is_connected():
                await client.connect()
                
            entity = await client.get_entity(channel)
            
            # Search for messages on the specific date
            async for message in client.iter_messages(
                entity,
                offset_date=end_of_day,
                reverse=True
            ):
                # Stop if we've gone past the target date
                if message.date < start_of_day:
                    break
                    
                # Only process messages from the target date
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
                            doc.attributes[0].file_name and 
                            doc.attributes[0].file_name.lower().endswith('.txt')
                        )
                    )
                    
                    if is_text_file:
                        try:
                            # Download file content directly to memory
                            file_bytes = await client.download_media(message, bytes)
                            
                            if file_bytes:
                                # Process the file content directly from memory
                                file_text = file_bytes.decode('utf-8', errors='ignore')
                                lines = file_text.splitlines()
                                
                                for line in lines:
                                    line = line.strip()
                                    if (
                                        line and 
                                        not PROXY_PATTERN.match(line) and 
                                        EMAIL_PASS_PATTERN.match(line)
                                    ):
                                        all_lines.add(line)
                                        
                        except Exception:
                            continue
            
        except Exception:
            continue
    
    return list(all_lines)

async def scrape_files(client, target_date):
    """Scrape files from all channel groups one by one"""
    all_lines = set()
    
    for channel_group in CHANNEL_GROUPS:
        try:
            group_lines = await scrape_files_from_group(client, channel_group, target_date)
            all_lines.update(group_lines)
        except Exception:
            continue
    
    return list(all_lines)

async def send_results(bot_client, user_id, lines):
    """Send processed results to user - entirely in memory"""
    if not lines:
        await bot_client.send_message(user_id, "❌ No valid combos found for the specified date.")
        return
    
    random.shuffle(lines)
    chunk_size = random.randint(50000, 70000)
    chunks = [lines[i:i + chunk_size] for i in range(0, len(lines), chunk_size)]
    
    for i, chunk in enumerate(chunks, 1):
        # Create file in memory
        file_content = '\n'.join(chunk)
        file_bytes = file_content.encode('utf-8')
        file_io = io.BytesIO(file_bytes)
        file_io.name = f"combos_{i}.txt"
        
        try:
            await bot_client.send_file(
                user_id,
                file_io,
                caption=f"📅 Part {i}/{len(chunks)} | 📝 {len(chunk):,} lines\n🔄 Mixed & Deduplicated"
            )
            
        except Exception:
            # Try to send an error message
            try:
                await bot_client.send_message(
                    user_id,
                    f"❌ Error sending part {i}"
                )
            except:
                pass

async def setup_bot_handlers(bot_client, user_client):
    """Configure bot command handlers"""
    @bot_client.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        await event.reply("""🤖 **Combo Scraper Bot**\n\n"""
                        """Send a date in DD.MM.YYYY format to scrape combos from that day.\n"""
                        """Example: `09.08.2025`\n\n"""
                        """Use /ping to test bot response time and download speed""")

    @bot_client.on(events.NewMessage(pattern='/ping'))
    async def ping_handler(event):
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
        except Exception:
            speed_test_result = {"success": False, "error": "Download test error"}
        
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

    @bot_client.on(events.NewMessage())
    async def message_handler(event):
        # Ignore commands other than /start and /ping
        if event.text.startswith('/') and event.text not in ['/start', '/ping']:
            return
        
        try:
            input_date = datetime.strptime(event.text, '%d.%m.%Y').date()
            current_date = datetime.now().date()
            
            # Allow dates up to the current date (not future dates)
            if input_date > current_date:
                await event.reply("❌ Future dates not allowed. Enter today's date or a past date.")
                return
                
            # Don't allow dates too far in the past (adjust as needed)
            if input_date < current_date - timedelta(days=30):
                await event.reply("❌ Date is too far in the past. Please select a date within the last 30 days.")
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
    
    await bot_client.run_until_disconnected()
    
    # Cleanup
    await user_client.disconnect()

if __name__ == '__main__':
    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Run application
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    except Exception:
        pass
    finally:
        loop.close()
