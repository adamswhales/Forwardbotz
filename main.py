import os, sqlite3
from pyrogram import Client, filters, types
from keep_alive import keep_alive

# ─── ENVIRONMENT VARIABLES ───
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
OWNER_ID = int(os.getenv("OWNER_ID"))

# ─── DATABASE SETUP ───
DB_PATH = "database.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS sources (chat_id TEXT PRIMARY KEY)")
conn.commit()

def set_setting(key, value):
    cursor.execute("INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)", (key, value))
    conn.commit()

def get_setting(key):
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cursor.fetchone()
    return row[0] if row else None

def add_source(chat_id):
    cursor.execute("INSERT OR IGNORE INTO sources (chat_id) VALUES (?)", (str(chat_id),))
    conn.commit()

def remove_source(chat_id):
    cursor.execute("DELETE FROM sources WHERE chat_id=?", (str(chat_id),))
    conn.commit()

def list_sources():
    cursor.execute("SELECT chat_id FROM sources")
    return [int(r[0]) for r in cursor.fetchall()]

# ─── DYNAMIC SETTINGS ───
SOURCE_CHATS = set(list_sources())
TARGET_CHAT = int(get_setting("target") or 0) or None

app = Client("forwarder", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# ─── COMMANDS ───
@app.on_message(filters.user(OWNER_ID) & filters.command("help"))
async def cmd_help(client, message):
    help_text = """
Auto Forward Bot Commands:

/addsource -100123456789 → Add a source channel
/removesource -100123456789 → Remove a source channel
/listsources → Show all sources
/settarget -100987654321 → Set the target channel
/status → Show current setup
/help → Show this help message
"""
    await message.reply_text(help_text)

@app.on_message(filters.user(OWNER_ID) & filters.command("addsource"))
async def cmd_add_source(client, message):
    try:
        chat_id = int(message.text.split(" ", 1)[1])
        add_source(chat_id)
        SOURCE_CHATS.add(chat_id)
        await message.reply_text(f"✅ Added source: `{chat_id}`")
    except:
        await message.reply_text("❌ Usage: `/addsource -100123456789`")

@app.on_message(filters.user(OWNER_ID) & filters.command("removesource"))
async def cmd_remove_source(client, message):
    try:
        chat_id = int(message.text.split(" ", 1)[1])
        remove_source(chat_id)
        SOURCE_CHATS.discard(chat_id)
        await message.reply_text(f"🗑 Removed source: `{chat_id}`")
    except:
        await message.reply_text("❌ Usage: `/removesource -100123456789`")

@app.on_message(filters.user(OWNER_ID) & filters.command("listsources"))
async def cmd_list_sources(client, message):
    sources = list_sources()
    if sources:
        sources_text = "\n".join([f"- `{s}`" for s in sources])
        await message.reply_text(f"📌 Sources:\n{sources_text}")
    else:
        await message.reply_text("⚠️ No sources set yet.")

@app.on_message(filters.user(OWNER_ID) & filters.command("settarget"))
async def cmd_set_target(client, message):
    global TARGET_CHAT
    try:
        TARGET_CHAT = int(message.text.split(" ", 1)[1])
        set_setting("target", str(TARGET_CHAT))
        await message.reply_text(f"✅ Target set to `{TARGET_CHAT}`")
    except:
        await message.reply_text("❌ Usage: `/settarget -100987654321`")

@app.on_message(filters.user(OWNER_ID) & filters.command("status"))
async def cmd_status(client, message):
    sources = list_sources()
    sources_text = "\n".join([f"- `{s}`" for s in sources]) if sources else "None"
    target = f"`{TARGET_CHAT}`" if TARGET_CHAT else "None"
    await message.reply_text(f"📌 Sources:\n{sources_text}\n\n🎯 Target: {target}")

# ─── FORWARDING ───
@app.on_message()
async def forward_message(client, message: types.Message):
    global TARGET_CHAT
    if TARGET_CHAT and message.chat.id in SOURCE_CHATS:
        try:
            if message.reply_markup:  # remove inline buttons
                await message.copy(TARGET_CHAT, reply_markup=None)
            else:
                await message.copy(TARGET_CHAT)
            print(f"✅ Forwarded from {message.chat.id}: {message.id}")
        except Exception as e:
            print(f"❌ Error: {e}")

# ─── START BOT ───
if __name__ == "__main__":
    keep_alive()
    app.run()
