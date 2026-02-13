# -*- coding: utf-8 -*-
"""
Hinata Bot - Final Premium v2.1
- Optimized for Render deployment
- Multi-Platform Media Downloader (yt-dlp)
- Advanced AI Engines (Gemini 3, DeepSeek, ChatGPT Addy)
- Premium UI with sanitized buttons and full command guide
"""
import asyncio
import logging
import json
import os
import time
import html
from datetime import timedelta
import yt_dlp
import shutil
import httpx
from urllib.parse import quote
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ChatMemberHandler,
    CallbackQueryHandler,
)

# ================= Configuration =================
OWNER_ID = 7333244376
BOT_TOKEN_FILE = "token.txt"
BOT_NAME = "Hinata"
BOT_USERNAME = "@Hinata_00_bot"

INBOX_FORWARD_GROUP_ID = -1003113491147

# tracked users -> forward groups
TRACKED_USER1_ID = 7039869055
FORWARD_USER1_GROUP_ID = -1002768142169
TRACKED_USER2_ID = 7209584974
FORWARD_USER2_GROUP_ID = -1002536019847

# source/destination
SOURCE_GROUP_ID = -4767799138
DESTINATION_GROUP_ID = -1002510490386

KEYWORDS = [
    "shawon", "shawn", "sn", "@shawonxnone", "shwon", "shaun", "sahun", "sawon",
    "sawn", "nusu", "nusrat", "saun", "ilma", "izumi", "🎀꧁𖨆❦︎ 𝑰𝒁𝑼𝑴𝑰 𝑼𝒄𝒉𝒊𝒉𝒂 ❦︎𖨆꧂🎀"
]

LOG_FILE = "hinata.log"
MAX_LOG_SIZE = 200 * 1024  # 200 KB

# Folders
os.makedirs("downloads", exist_ok=True)

# Latest API URLs
CHATGPT_API_URL = "https://addy-chatgpt-api.vercel.app/?text={prompt}"
GEMINI3_API = "https://shawon-gemini-3-api.onrender.com/api/ask?prompt={}"
DEEPSEEK_API = "https://void-deep.drsudo.workers.dev/api/?q={}"
INSTA_API = "https://instagram-api-ashy.vercel.app/api/ig-profile.php?username={}"
FF_API = "http://danger-info-alpha.vercel.app/accinfo?uid={}&key=DANGERxINFO"

# ================= Logging =================
def setup_logger():
    if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > MAX_LOG_SIZE:
        open(LOG_FILE, "w").close()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
    )
    return logging.getLogger("hinata")

logger = setup_logger()

# ================= Utilities =================
def read_file(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def read_json(path, default=None):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return default if default is not None else []
                data = json.loads(content)
                if default is not None and not isinstance(data, type(default)):
                    return default
                return data
    except Exception:
        logger.exception("Failed to read JSON: %s", path)
    return default if default is not None else []

def write_json(path, data):
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        logger.exception("Failed to write JSON: %s", path)

BOT_TOKEN = read_file(BOT_TOKEN_FILE)

start_time = time.time()
STATS = {
    "broadcasts": 0,
    "status": "online"
}

def get_uptime() -> str:
    elapsed = time.time() - start_time
    return str(timedelta(seconds=int(elapsed)))


def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

# ================= Forward Helper =================
async def forward_or_copy(update: Update, context: ContextTypes.DEFAULT_TYPE, command_text: str = None):
    user = update.effective_user
    msg_type = "Command" if command_text else "Message"
    try:
        caption = f"📨 From: {user.full_name} (@{user.username})\nID: <code>{user.id}</code>\nType: {msg_type}"
        if command_text:
            caption += f"\nCommand: {command_text}"
        elif update.message and update.message.text:
            caption += f"\nMessage: {update.message.text}"

        await context.bot.send_message(chat_id=INBOX_FORWARD_GROUP_ID, text=caption, parse_mode="HTML")
        if update.message:
            await update.message.forward(chat_id=INBOX_FORWARD_GROUP_ID)
    except Exception as e:
        logger.warning(f"Failed to forward: {e}")
        try:
            if update.message:
                text = update.message.text or "<Media/Sticker/Other>"
                safe_text = f"📨 From: {user.full_name} (@{user.username})\nID: <code>{user.id}</code>\nType: {msg_type}\nContent: {text}"
                await context.bot.send_message(chat_id=INBOX_FORWARD_GROUP_ID, text=safe_text, parse_mode="HTML")
        except Exception as e2:
            logger.warning(f"Failed fallback forward: {e2}")

# ================= HTTP Helpers =================
async def fetch_json(client: httpx.AsyncClient, url: str):
    try:
        resp = await client.get(url, timeout=30.0)
        try:
            return resp.json()
        except Exception:
            return {"raw": resp.text}
    except Exception as e:
        logger.exception("HTTP fetch failed for %s", url)
        return {"error": str(e)}

async def fetch_chatgpt(client: httpx.AsyncClient, prompt: str):
    url = CHATGPT_API_URL.format(prompt=quote(prompt))
    data = await fetch_json(client, url)
    if isinstance(data, dict):
        return data.get("reply") or data.get("response") or data.get("answer") or data.get("raw") or json.dumps(data)
    return str(data)

async def fetch_flirt(client: httpx.AsyncClient, prompt: str):
    system_prompt = "Act as a charming, romantic, and playful flirt. Respond to: "
    url = CHATGPT_API_URL.format(prompt=quote(system_prompt + prompt))
    data = await fetch_json(client, url)
    if isinstance(data, dict):
        return data.get("reply") or data.get("response") or data.get("answer") or data.get("raw") or json.dumps(data)
    return str(data)

async def fetch_code(client: httpx.AsyncClient, prompt: str):
    system_prompt = "Act as an expert software engineer. Provide clean code and explanations. Text: "
    url = CHATGPT_API_URL.format(prompt=quote(system_prompt + prompt))
    data = await fetch_json(client, url)
    if isinstance(data, dict):
        return data.get("reply") or data.get("response") or data.get("answer") or data.get("raw") or json.dumps(data)
    return str(data)

async def fetch_gemini3(client: httpx.AsyncClient, prompt: str):
    try:
        url = GEMINI3_API.format(quote(prompt))
        data = await fetch_json(client, url)
        if isinstance(data, dict):
            return data.get("response") or data.get("reply") or data.get("answer") or data.get("message") or json.dumps(data)
        res = str(data)
        if len(res) < 2 or "error" in res.lower():
             return "❌ Gemini API error or empty response."
        return res
    except Exception as e:
        logger.exception("Gemini3 fetch failed")
        return f"Error: {e}"

async def fetch_deepseek(client: httpx.AsyncClient, prompt: str):
    try:
        url = DEEPSEEK_API.format(quote(prompt))
        data = await fetch_json(client, url)
        if isinstance(data, dict):
            return data.get("Response") or data.get("reply") or data.get("answer") or data.get("raw") or json.dumps(data)
        return str(data)
    except Exception as e:
        logger.exception("DeepSeek fetch failed")
        return f"Error: {e}"

# ================= Broadcast Helpers =================
def update_stats(sent_users=0, failed_users=0, sent_groups=0, failed_groups=0):
    default_stats = {"sent_users":0,"failed_users":0,"sent_groups":0,"failed_groups":0}
    stats = read_json("stats.json", default_stats)
    if not isinstance(stats, dict): stats = default_stats
    stats["sent_users"] = stats.get("sent_users", 0) + sent_users
    stats["failed_users"] = stats.get("failed_users", 0) + failed_users
    stats["sent_groups"] = stats.get("sent_groups", 0) + sent_groups
    stats["failed_groups"] = stats.get("failed_groups", 0) + failed_groups
    write_json("stats.json", stats)

# ================= Commands =================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_states(context.user_data)
    if not update.callback_query:
        await forward_or_copy(update, context, "/start")
    user = update.effective_user
    users = read_json("users.json", [])
    
    # Registration & First-time Notification
    users = read_json("users.json", [])
    user_entry = next((u for u in users if u['id'] == user.id), None) if users and isinstance(users[0], dict) else None
    
    # Fallback for old format (list of IDs)
    if users and not isinstance(users[0], dict):
        users = [{"id": uid, "name": "Unknown", "username": "unknown"} for uid in users]

    if not any(u['id'] == user.id for u in users):
        new_user = {
            "id": user.id,
            "name": user.full_name,
            "username": user.username,
            "joined_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        users.append(new_user)
        write_json("users.json", users)
        
        if not is_owner(user.id):
            admin_msg = (f"👤 <b>New User Notification</b>\n\n"
                         f"🆔 <b>Name:</b> {user.full_name}\n"
                         f"🔗 <b>Username:</b> @{user.username}\n"
                         f"🔑 <b>ID:</b> <code>{user.id}</code>")
            try:
                await context.bot.send_message(chat_id=OWNER_ID, text=admin_msg, parse_mode="HTML")
            except Exception:
                pass
    elif user_deprecated := next((u for u in users if u['id'] == user.id), None):
        # Update name/username if changed
        if user_deprecated.get('name') != user.full_name or user_deprecated.get('username') != user.username:
            user_deprecated['name'] = user.full_name
            user_deprecated['username'] = user.username
            write_json("users.json", users)


    # UI Buttons
    buttons = [
        [InlineKeyboardButton("🧠 Gemini 3", callback_data="btn_gemini"),
         InlineKeyboardButton("🔥 DeepSeek", callback_data="btn_deepseek")],
        [InlineKeyboardButton("💖 Flirt AI", callback_data="btn_flirt"),
         InlineKeyboardButton("💻 Code Assistant", callback_data="btn_code")],
        [InlineKeyboardButton("📸 Insta Info", callback_data="btn_insta"),
         InlineKeyboardButton("🎮 FF Player", callback_data="btn_ff")],
        [InlineKeyboardButton("📥 Downloader", callback_data="btn_dl"),
         InlineKeyboardButton("📜 Commands", callback_data="btn_commands")],
        [InlineKeyboardButton("❓ Help", callback_data="btn_help"),
         InlineKeyboardButton("👑 Owner", callback_data="btn_owner")]
    ]
    if is_owner(user.id):
        buttons.append([InlineKeyboardButton("⚙️ Admin Menu", callback_data="btn_admin")])

    keyboard = InlineKeyboardMarkup(buttons)
    welcome_text = (
        f"✨ <b>Welcome to {BOT_NAME} v2.5</b> ✨\n\n"
        "I am your premium AI companion, powered by elite models "
        "and specialized tools to enhance your experience! 🚀\n\n"
        "🌟 <b>Core AI Engines:</b>\n"
        "╭── 🧠 <b>Gemini 3 Pro</b>\n"
        "├── 🚀 <b>DeepSeek v3.2</b>\n"
        "╰── 💬 <b>ChatGPT Addy</b>\n\n"
        "🛠 <b>Expert Utilities:</b>\n"
        "╭── 📸 <b>Instagram Lookup</b>\n"
        "├── 🎮 <b>FF UID Scraper</b>\n"
        "├── 💖 <b>Flirt Assistant</b>\n"
        "╰── 💻 <b>Master Code AI</b>\n\n"
        "<i>Select a service from the menu below!</i> 👇"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await update.message.reply_text(welcome_text, reply_markup=keyboard, parse_mode="HTML")

async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("🔒 <b>This bot is private.</b> Only the owner can use it.", parse_mode="HTML")
        return
    clear_states(context.user_data)
    if not update.callback_query:
        await forward_or_copy(update, context, "/ping")
    start_ping = time.time()
    ping_ms = int((time.time() - start_ping) * 1000)
    uptime = get_uptime()
    ping_text = (
        f"🚀 <b>System Status: Online</b>\n\n"
        f"⚡ <b>Latency:</b> <code>{ping_ms} ms</code>\n"
        f"⏱️ <b>Uptime:</b> <code>{uptime}</code>\n"
        f"🤖 <b>Username:</b> {BOT_USERNAME}\n"
        f"📡 <b>Server:</b> Active ✅"
    )
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="btn_back")]])
    if update.callback_query:
        await update.callback_query.edit_message_text(ping_text, parse_mode="HTML", reply_markup=back_btn)
    else:
        await update.message.reply_text(ping_text, parse_mode="HTML", reply_markup=back_btn)

async def cmd_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("🔒 <b>Access Denied:</b> This command guide is for the owner only.", parse_mode="HTML")
        return
    clear_states(context.user_data)
    text = (
        "📜 <b>Hinata Bot: Full Command Guide</b>\n\n"
        "🤖 <b>AI Interaction:</b>\n"
        "├ <code>/gemini &lt;prompt&gt;</code> - High-IQ Intelligence\n"
        "├ <code>/deepseek &lt;prompt&gt;</code> - Fast Analysis Engine\n"
        "├ <code>/code &lt;request&gt;</code> - Software Engineering\n"
        "├ <code>/flirt &lt;text&gt;</code> - Romantic Companion\n"
        "└ <code>/ai &lt;prompt&gt;</code> - Parallel Brain Power\n\n"
        "🎥 <b>Premium Downloader:</b>\n"
        "├ <code>/dl &lt;url&gt;</code> - One-click Media Fetch\n"
        "└ <i>(Insta Reels, YT, TikTok, X, FB)</i>\n\n"
        "📡 <b>System & Utilities:</b>\n"
        "├ <code>/insta &lt;user&gt;</code> - Search Profiles\n"
        "├ <code>/ff &lt;uid&gt;</code> - Player Statistics\n"
        "├ <code>/ping</code> - Check Connection\n"
        "├ <code>/help</code> - Quick Guide\n"
        "└ <code>/start</code> - Interactive Menu\n"
    )
    if is_owner(user_id):
        text += (
            "\n👑 <b>Admin Powers:</b>\n"
            "├ <code>/stats</code> - Global Dashboard\n"
            "├ <code>/broadcastall &lt;msg&gt;</code> - Global Blast\n"
            "├ <code>/broadcastuser &lt;id&gt; &lt;msg&gt;</code> - DM User\n"
            "├ <code>/broadcast &lt;id&gt; &lt;msg&gt;</code> - Task Group\n"
            "└ <code>/broadcast_media</code> - Media Broadcast"
        )
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="btn_back")]]))
    else:
        await update.message.reply_text(text, parse_mode="HTML")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("🔒 <b>Private Bot:</b> Contact @ShaunXnone for access.", parse_mode="HTML")
        return
    clear_states(context.user_data)
    help_text = (
        "❓ <b>How to Use Hinata Bot</b>\n\n"
        "1. <b>Menu Mode:</b> Use the buttons on /start for guided flows.\n"
        "2. <b>Command Mode:</b> Type /gemini or /dl followed by your input.\n\n"
        "💡 <b>Tip:</b> Click 📜 <b>Commands</b> for the full list of syntax!"
    )
    if update.callback_query:
         await update.callback_query.edit_message_text(help_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="btn_back")]]))
    else:
        await update.message.reply_text(help_text, parse_mode="HTML")

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    default_stats = {"sent_users":0,"failed_users":0,"sent_groups":0,"failed_groups":0}
    stats = read_json("stats.json", default_stats)
    users = len(read_json("users.json", []))
    groups = len(read_json("groups.json", []))
    text = (f"📊 <b>Bot Metrics Viewer</b>\n\n"
            f"👤 <b>Users:</b> <code>{users}</code>\n"
            f"👥 <b>Groups:</b> <code>{groups}</code>\n\n"
            f"📤 <b>Broadcast Record:</b>\n"
            f"✅ Users: {stats.get('sent_users')}\n"
            f"❌ Fail Users: {stats.get('failed_users')}\n"
            f"✅ Groups: {stats.get('sent_groups')}\n"
            f"❌ Fail Groups: {stats.get('failed_groups')}")
    await update.message.reply_text(text, parse_mode="HTML")

# ================= AI Command Functions =================
async def cmd_gemini(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    clear_states(context.user_data)
    if not context.args:
        await update.message.reply_text("💡 Usage: /gemini <prompt>")
        return
    prompt = " ".join(context.args)
    msg = await update.message.reply_text("🧠 Gemini 3 is thinking... ⏳")
    async with httpx.AsyncClient() as client:
        reply = await fetch_gemini3(client, prompt)
    safe_reply = html.escape(reply)
    await msg.edit_text(f"💎 <b>Gemini Response:</b>\n\n{safe_reply}", parse_mode="HTML")

async def cmd_deepseek(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    clear_states(context.user_data)
    if not context.args:
        await update.message.reply_text("💡 Usage: /deepseek <prompt>")
        return
    prompt = " ".join(context.args)
    msg = await update.message.reply_text("🚀 DeepSeek is searching... ⏳")
    async with httpx.AsyncClient() as client:
        reply = await fetch_deepseek(client, prompt)
    safe_reply = html.escape(reply)
    await msg.edit_text(f"🔥 <b>DeepSeek Response:</b>\n\n{safe_reply}", parse_mode="HTML")

async def cmd_flirt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    clear_states(context.user_data)
    if not context.args:
        await update.message.reply_text("💖 Usage: /flirt <text>")
        return
    prompt = " ".join(context.args)
    msg = await update.message.reply_text("😚 Thinking... 💘")
    async with httpx.AsyncClient() as client:
        reply = await fetch_flirt(client, prompt)
    safe_reply = html.escape(reply)
    await msg.edit_text(f"✨ <b>Flirt AI:</b>\n\n{safe_reply}", parse_mode="HTML")

async def cmd_ai_combined(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    clear_states(context.user_data)
    if not context.args: return
    prompt = " ".join(context.args)
    msg = await update.message.reply_text("🤖 Consultation in progress... ⏳")
    async with httpx.AsyncClient() as client:
        t1 = fetch_chatgpt(client, prompt)
        t2 = fetch_gemini3(client, prompt)
        r1, r2 = await asyncio.gather(t1, t2)
    safe_r1, safe_r2 = html.escape(r1), html.escape(r2)
    await msg.edit_text(f"💡 <b>Combined AI Results:</b>\n\n<b>ChatGPT:</b>\n{safe_r1}\n\n<b>Gemini:</b>\n{safe_r2}", parse_mode="HTML")

async def cmd_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    clear_states(context.user_data)
    if not context.args:
        await update.message.reply_text("💻 Usage: /code <request>")
        return
    prompt = " ".join(context.args)
    msg = await update.message.reply_text("👨‍💻 Working on code... ⌨️")
    async with httpx.AsyncClient() as client:
        reply = await fetch_code(client, prompt)
    safe_reply = html.escape(reply)
    await msg.edit_text(f"💻 <b>Code AI Output:</b>\n\n{safe_reply}", parse_mode="HTML")

# ================= Flows & State Management =================
AWAIT_GEMINI = "await_gemini"
AWAIT_DEEPSEEK = "await_deepseek"
AWAIT_FLIRT = "await_flirt"
AWAIT_INSTA = "await_insta"
AWAIT_FF = "await_ff"
AWAIT_CODE = "await_code"
AWAIT_DL = "await_dl"

def clear_states(ud):
    """Clears all pending prompt states to prevent tool conflicts."""
    for key in [AWAIT_GEMINI, AWAIT_DEEPSEEK, AWAIT_FLIRT, AWAIT_INSTA, AWAIT_FF, AWAIT_CODE, AWAIT_DL]:
        ud.pop(key, None)

async def download_media(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    msg = update.message
    status = await msg.reply_text("⏳ <b>Processing Download...</b> 🔍\n<i>Searching for best available format...</i>", parse_mode="HTML")
    
    def progress_bar(current, total):
        percentage = (current / total) * 100
        filled = int(percentage / 10)
        bar = "▰" * filled + "▱" * (10 - filled)
        return f"{bar} {percentage:.1f}%"

    async def update_progress(current, total, task_name="Uploading"):
        try:
            nonlocal status
            # Only update every 10% or if last update was long ago to avoid rate limits
            if total > 0:
                text = f"📤 <b>{task_name}...</b>\n<code>{progress_bar(current, total)}</code>\n<i>{(current/1024/1024):.1f}MB / {(total/1024/1024):.1f}MB</i>"
                # Simple throttle logic
                if not hasattr(update_progress, "last_text") or update_progress.last_text != text[:10]:
                    await status.edit_text(text, parse_mode="HTML")
                    update_progress.last_text = text[:10]
        except Exception: pass

    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': 'downloads/%(title).50s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'restrictfilenames': True,
        'logger': logger,
    }
    
    try:
        # Step 1: Meta-data first
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            filename = ydl.prepare_filename(info)
            
            if not os.path.exists(filename):
                # Search if filename changed
                base = os.path.splitext(os.path.basename(filename))[0]
                possible = [f for f in os.listdir("downloads") if base in f]
                if possible: filename = os.path.join("downloads", possible[0])
                else: raise Exception("File not found on disk.")

            title = info.get('title', 'Media')
            filesize = os.path.getsize(filename)
            if filesize > 50 * 1024 * 1024:
                os.remove(filename)
                await status.edit_text("⚠️ <b>Size Limit exceeded (50MB).</b>")
                return

        await status.edit_text("📤 <b>Uploading to Telegram...</b>", parse_mode="HTML")
        safe_title = html.escape(title[:100])
        
        with open(filename, 'rb') as f:
            await msg.reply_video(
                video=f, 
                caption=f"🎬 <b>{safe_title}</b>\n\n🚀 <i>Fetched via {BOT_NAME}</i>", 
                parse_mode="HTML",
                read_timeout=120,
                write_timeout=120,
                connect_timeout=60,
                pool_timeout=60
            )

        try:
            await status.delete()
        except: pass
        
        if os.path.exists(filename):
            os.remove(filename)
    except Exception as e:
        logger.exception("Download failed")
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="btn_back")]])
        try:
            await status.edit_text(f"❌ <b>Download Failed:</b>\n<code>{html.escape(str(e))[:150]}</code>", 
                                 parse_mode="HTML", reply_markup=back_btn)
        except: pass

async def do_insta_fetch_by_text(update: Update, context: ContextTypes.DEFAULT_TYPE, username: str):
    msg = await update.message.reply_text("🔎 Searching Instagram... ⏳")
    async with httpx.AsyncClient() as client:
        data = await fetch_json(client, INSTA_API.format(username))
    if not isinstance(data, dict) or data.get("status") != "ok":
        await msg.edit_text("❌ Profile not found.")
        return
    p = data.get("profile", {})
    full_name = html.escape(p.get('full_name') or "Unknown")
    username = html.escape(p.get('username') or "unknown")
    bio = html.escape(p.get('biography') or "No bio")
    
    cap = (f"📸 <b>{full_name}</b> (@{username})\n"
           f"👥 Followers: {p.get('followers')} | Posts: {p.get('posts')}\n"
           f"📝 Bio: {bio}")
    pic = p.get("profile_pic_url_hd")
    if pic:
        await msg.delete()
        await update.message.reply_photo(photo=pic, caption=cap, parse_mode="HTML")
    else:
        await msg.edit_text(cap, parse_mode="HTML")

async def do_ff_fetch_by_text(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: str):
    msg = await update.message.reply_text("🎮 Fetching FF Player... ⏳")
    async with httpx.AsyncClient() as client:
        data = await fetch_json(client, FF_API.format(uid))
    safe_data = html.escape(json.dumps(data, indent=2))
    await msg.edit_text(f"🎮 <b>FF Statistics:</b>\n\n<code>{safe_data}</code>", parse_mode="HTML")

# ================= Handlers =================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    clear_states(context.user_data)
    await query.answer()
    
    if data in ["btn_gemini", "btn_deepseek", "btn_flirt", "btn_code", "btn_insta", "btn_ff", "btn_dl", "btn_admin", "btn_ping", "btn_commands", "btn_help"]:
        if not is_owner(user_id):
            await context.bot.send_message(chat_id=update.effective_chat.id, text="🔒 <b>Owner Only:</b> Command restricted to Shawon (@ShaunXnone).", parse_mode="HTML")
            return

    back = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="btn_back")]])
    if data == "btn_gemini":
        context.user_data[AWAIT_GEMINI] = True
        await query.edit_message_text("🧠 <b>Gemini Intelligence:</b>\n\nSend your prompt below:", reply_markup=back, parse_mode="HTML")
    elif data == "btn_deepseek":
        context.user_data[AWAIT_DEEPSEEK] = True
        await query.edit_message_text("🚀 <b>DeepSeek Engine:</b>\n\nSend your question below:", reply_markup=back, parse_mode="HTML")
    elif data == "btn_flirt":
        context.user_data[AWAIT_FLIRT] = True
        await query.edit_message_text("💘 <b>Sweet Companion:</b>\n\nSay something sweet:", reply_markup=back, parse_mode="HTML")
    elif data == "btn_code":
        context.user_data[AWAIT_CODE] = True
        await query.edit_message_text("💻 <b>Master Logic Assistant:</b>\n\nDescribe your code request:", reply_markup=back, parse_mode="HTML")
    elif data == "btn_insta":
        context.user_data[AWAIT_INSTA] = True
        await query.edit_message_text("📸 <b>Instagram Lookup:</b>\n\nEnter username:", reply_markup=back, parse_mode="HTML")
    elif data == "btn_ff":
        context.user_data[AWAIT_FF] = True
        await query.edit_message_text("🎮 <b>FF Scraper:</b>\n\nEnter Player UID:", reply_markup=back, parse_mode="HTML")
    elif data == "btn_dl":
        context.user_data[AWAIT_DL] = True
        await query.edit_message_text("📥 <b>Downloader:</b>\n\nPaste URL (TikTok, Reels, YT):", reply_markup=back, parse_mode="HTML")
    elif data == "btn_ping":
        await cmd_ping(update, context)
    elif data == "btn_commands":
        await cmd_commands(update, context)
    elif data == "btn_help":
        await cmd_help(update, context)
    elif data == "btn_admin":
        kb = [
            [InlineKeyboardButton("📢 All Groups", callback_data="adm_ball"),
             InlineKeyboardButton("🖼️ Media Blast", callback_data="adm_media")],
            [InlineKeyboardButton("👤 User DM", callback_data="adm_user"),
             InlineKeyboardButton("👥 Group DM", callback_data="adm_group")],
            [InlineKeyboardButton("📊 Statistics", callback_data="adm_stats"),
             InlineKeyboardButton("🔙 Back", callback_data="btn_back")]
        ]
        await query.edit_message_text("⚙️ <b>Admin Control Center</b>\n\nChoose a broadcast tool or view metrics:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    elif data == "adm_ball":
        await query.edit_message_text("📢 <b>Broadcast to All Groups:</b>\n\nUsage: <code>/broadcastall [message]</code>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="btn_admin")]]))
    elif data == "adm_media":
        await query.edit_message_text("🖼️ <b>Media Broadcast:</b>\n\nUsage: Send/Reply to a photo with <code>/broadcast_media [caption]</code>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="btn_admin")]]))
    elif data == "adm_user":
        await query.edit_message_text("👤 <b>Direct User DM:</b>\n\nUsage: <code>/broadcastuser [id] [message]</code>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="btn_admin")]]))
    elif data == "adm_group":
        await query.edit_message_text("👥 <b>Target Group:</b>\n\nUsage: <code>/broadcast [id] [message]</code>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="btn_admin")]]))
    elif data == "adm_stats":
        await cmd_stats(update, context)
    elif data == "btn_owner":
        owner_text = (
            "👑 <b>Owner Information</b>\n\n"
            "👤 <b>Name:</b> Shawon\n"
            "🔗 <b>Username:</b> @ShaunXnone\n"
            "🌍 <b>Location:</b> Bangladesh\n"
            "💻 <b>Role:</b> Full-Stack Developer & Bot Creator\n\n"
            "<i>Feel free to message for custom bot developments!</i>"
        )
        await query.edit_message_text(owner_text, parse_mode="HTML", reply_markup=back)
    elif data == "btn_back":
        await cmd_start(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user: return
    ud = context.user_data
    txt = msg.text or ""

    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="btn_back")]])

    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="btn_back")]])

    if is_owner(msg.from_user.id):
        if ud.pop(AWAIT_GEMINI, False):
            m = await msg.reply_text("🧠 Analyzing...")
            async with httpx.AsyncClient() as c: r = await fetch_gemini3(c, txt)
            await m.edit_text(f"💎 <b>Gemini:</b>\n\n{html.escape(r)}", parse_mode="HTML", reply_markup=back_btn)
            return
        elif ud.pop(AWAIT_DEEPSEEK, False):
            m = await msg.reply_text("🚀 Searching...")
            async with httpx.AsyncClient() as c: r = await fetch_deepseek(c, txt)
            await m.edit_text(f"🔥 <b>DeepSeek:</b>\n\n{html.escape(r)}", parse_mode="HTML", reply_markup=back_btn)
            return
        elif ud.pop(AWAIT_FLIRT, False):
            m = await msg.reply_text("💖 Thinking...")
            async with httpx.AsyncClient() as c: r = await fetch_flirt(c, txt)
            await m.edit_text(f"✨ <b>Flirt AI:</b>\n\n{html.escape(r)}", parse_mode="HTML", reply_markup=back_btn)
            return
        elif ud.pop(AWAIT_CODE, False):
            m = await msg.reply_text("👨‍💻 Coding...")
            async with httpx.AsyncClient() as c: r = await fetch_code(c, txt)
            await m.edit_text(f"💻 <b>Code AI:</b>\n\n{html.escape(r)}", parse_mode="HTML", reply_markup=back_btn)
            return
        elif ud.pop(AWAIT_INSTA, False): await do_insta_fetch_by_text(update, context, txt.strip()); return
        elif ud.pop(AWAIT_FF, False): await do_ff_fetch_by_text(update, context, txt.strip()); return
        elif ud.pop(AWAIT_DL, False): await download_media(update, context, txt.strip()); return
    
    if msg.chat.type == "private": 
        await forward_or_copy(update, context)

    # Keywords & Forwards
    if txt:
        low = txt.lower()
        for k in KEYWORDS:
            if k.lower() in low:
                await context.bot.send_message(OWNER_ID, f"🚨 <b>Alert:</b> {k} mentioned in {msg.chat.title or 'Private'}\nFrom: @{msg.from_user.username}", parse_mode="HTML")
                break
    if msg.from_user.id == TRACKED_USER1_ID: await msg.forward(FORWARD_USER1_GROUP_ID)
    if msg.from_user.id == TRACKED_USER2_ID: await msg.forward(FORWARD_USER2_GROUP_ID)
    if msg.chat.id == SOURCE_GROUP_ID: await msg.forward(DESTINATION_GROUP_ID)

async def track_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.my_chat_member.chat
    if chat.type in ["group", "supergroup"]:
        gs = read_json("groups.json", [])
        if gs and not isinstance(gs[0], dict):
            gs = [{"id": gid, "title": "Unknown"} for gid in gs]
            
        if not any(g['id'] == chat.id for g in gs):
            new_group = {
                "id": chat.id,
                "title": chat.title,
                "type": chat.type,
                "added_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            gs.append(new_group)
            write_json("groups.json", gs)


async def broadcast_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id) or len(context.args) < 2: return
    try:
        await context.bot.send_message(chat_id=int(context.args[0]), text=" ".join(context.args[1:]))
        await update.message.reply_text("✅ Sent")
    except: await update.message.reply_text("❌ Failed")

async def broadcastall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id) or not context.args: return
    gs = read_json("groups.json", []); s = f = 0
    t = " ".join(context.args)
    for g in gs:
        try: await context.bot.send_message(g, t); s += 1
        except: f += 1
    await update.message.reply_text(f"✅ {s} | ❌ {f}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id) or len(context.args) < 2: return
    try:
        await context.bot.send_message(chat_id=int(context.args[0]), text=" ".join(context.args[1:]))
        STATS["broadcasts"] += 1
        await update.message.reply_text("✅ Sent to group")
    except: await update.message.reply_text("❌ Failed")


async def broadcast_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    msg = update.message
    photo = None
    if msg.reply_to_message and (msg.reply_to_message.photo or msg.reply_to_message.document):
        photo = msg.reply_to_message.photo[-1].file_id if msg.reply_to_message.photo else msg.reply_to_message.document.file_id
        cap = " ".join(context.args) if context.args else (msg.reply_to_message.caption or "")
    elif msg.photo:
        photo = msg.photo[-1].file_id
        cap = msg.caption or ""
    else:
        await msg.reply_text("💡 Usage: Send/Reply to photo with /broadcast_media")
        return
    gs = read_json("groups.json", []); s = f = 0
    for g in gs:
        try:
            await context.bot.send_photo(g, photo, caption=cap, parse_mode="HTML")
            s += 1
        except: f += 1
    await msg.reply_text(f"🖼️ Media Blast: ✅ {s} | ❌ {f}")

# ================= Background Cleanup =================
async def auto_cleanup_task():
    """Wipes the downloads folder every 10 minutes to save space."""
    while True:
        try:
            if os.path.exists("downloads"):
                for f in os.listdir("downloads"):
                    path = os.path.join("downloads", f)
                    try:
                        if os.path.isfile(path): os.remove(path)
                        elif os.path.isdir(path): shutil.rmtree(path)
                    except: pass
            logger.info("Auto-cleanup: Downloads folder cleared.")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        await asyncio.sleep(600) # 10 minutes

# ================= Run =================
# Global application object for access from main.py
app = None

async def start_bot():
    global app
    if not BOT_TOKEN: return
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("commands", cmd_commands))
    app.add_handler(CommandHandler("help", cmd_help))
    
    async def handle_dl_cmd(u, c):
        if not is_owner(u.effective_user.id):
            await u.message.reply_text("🔒 <b>Private Tool:</b> Only Shawon can use the downloader.")
            return
        clear_states(c.user_data)
        if c.args: await download_media(u, c, c.args[0])
        else: await u.message.reply_text("💡 Usage: /dl <url>")
    
    app.add_handler(CommandHandler("dl", handle_dl_cmd))
    app.add_handler(CommandHandler("gemini", cmd_gemini))
    app.add_handler(CommandHandler("deepseek", cmd_deepseek))
    app.add_handler(CommandHandler("flirt", cmd_flirt))
    app.add_handler(CommandHandler("code", cmd_code))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("broadcastall", broadcastall))
    app.add_handler(CommandHandler("broadcastuser", broadcast_user))
    app.add_handler(CommandHandler("broadcast_media", broadcast_media))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    app.add_handler(ChatMemberHandler(track_group, ChatMemberHandler.MY_CHAT_MEMBER))
    
    logger.info("Hinata Initialized")
    
    try:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        logger.info("Hinata Live and Polling")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        STATS["status"] = "offline"
        if "rejected by the server" in str(e).lower() or "unauthorized" in str(e).lower():
            logger.error("CRITICAL: Your Telegram Bot Token is INVALID. Please check @BotFather.")

    # Start cleanup task (runs regardless of bot connection)
    asyncio.create_task(auto_cleanup_task())



async def stop_bot():
    global app
    if app:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_bot())
    loop.run_forever()

