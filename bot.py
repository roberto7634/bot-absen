import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================= CONFIG =================
TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 8080))

DB_NAME = "data.db"

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_project(user_id, name):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO projects (user_id, name) VALUES (?, ?)", (user_id, name))
    conn.commit()
    conn.close()

def get_projects(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name FROM projects WHERE user_id=?", (user_id,))
    data = c.fetchall()
    conn.close()
    return data

def delete_project(project_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM projects WHERE id=?", (project_id,))
    conn.commit()
    conn.close()

# ================= MENU =================
def main_menu():
    keyboard = [
        [InlineKeyboardButton("➕ Tambah Project", callback_data="add")],
        [InlineKeyboardButton("📋 Lihat Project", callback_data="list")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ================= HANDLER =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Selamat datang!\nPilih menu:",
        reply_markup=main_menu()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "add":
        context.user_data["mode"] = "add"
        await query.message.reply_text("Kirim nama project:")

    elif query.data == "list":
        projects = get_projects(query.from_user.id)

        if not projects:
            await query.message.reply_text("Belum ada project.")
            return

        for pid, name in projects:
            keyboard = [[InlineKeyboardButton("❌ Hapus", callback_data=f"del_{pid}")]]
            await query.message.reply_text(
                f"📌 {name}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif query.data.startswith("del_"):
        pid = int(query.data.split("_")[1])
        delete_project(pid)
        await query.message.reply_text("✅ Project dihapus!")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("mode") == "add":
        add_project(update.message.from_user.id, update.message.text)
        context.user_data["mode"] = None
        await update.message.reply_text("✅ Project ditambahkan!", reply_markup=main_menu())

# ================= MAIN =================
async def main():
    if not TOKEN or not WEBHOOK_URL:
        raise ValueError("TOKEN dan WEBHOOK_URL harus di set di ENV!")

    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    await app.initialize()
    await app.start()

    # Set webhook
    await app.bot.set_webhook(f"{WEBHOOK_URL}/{TOKEN}")

    # Jalankan webhook server
    await app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}",
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())