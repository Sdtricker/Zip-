import os
import zipfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = "7930776122:AAGtn0YUQ0cDlvudPRrYUGxKBKJkG1IuMlw"
ADMIN_ID = 7467384643

# In-memory storage
data = {
    "welcome": "Welcome! Please upload your ZIP file.",
    "channels": [],
    "force_channel": None,
    "user_state": {}
}

os.makedirs("downloads", exist_ok=True)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Force join check
    if data["force_channel"]:
        keyboard = [[InlineKeyboardButton("JOINED", callback_data="check_join")]]
        for i in range(0, len(data["channels"]), 3):
            row = [InlineKeyboardButton("Channel", url=ch) for ch in data["channels"][i:i+3]]
            keyboard.insert(0, row)
        await update.message.reply_text("Please join all channels to continue.",
            reply_markup=InlineKeyboardMarkup(keyboard))
        data["user_state"][user_id] = {"stage": "wait_join"}
        return

    await update.message.reply_text(data["welcome"])
    data["user_state"][user_id] = {"stage": "awaiting_zip"}

# Admin command
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(
        "Admin Commands:\n/add LINK - Add channel\n/force LINK - Set force join channel\n/welcome TEXT - Set welcome msg"
    )

# Add channel
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if context.args:
        link = context.args[0]
        data["channels"].append(link)
        await update.message.reply_text("Channel added.")

# Set force join
async def force(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if context.args:
        link = context.args[0]
        data["force_channel"] = link
        await update.message.reply_text("Force join channel set.")

# Set welcome
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    msg = update.message.text.replace("/welcome", "").strip()
    data["welcome"] = msg
    await update.message.reply_text("Welcome message updated.")

# Handle ZIP and Passwords
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = data["user_state"].get(user_id, {}).get("stage")

    doc = update.message.document
    if not doc:
        return

    file_path = f"downloads/{user_id}_{doc.file_name}"
    new_file = await doc.get_file()
    await new_file.download_to_drive(file_path)

    if state == "awaiting_zip":
        data["user_state"][user_id] = {"stage": "awaiting_pass", "zip_path": file_path}
        await update.message.reply_text("Now send your password.txt file.")
    elif state == "awaiting_pass":
        zip_path = data["user_state"][user_id].get("zip_path")
        result = await try_passwords(zip_path, file_path)
        await update.message.reply_text(result, parse_mode="Markdown")
        data["user_state"][user_id] = {}

# Try passwords from txt
async def try_passwords(zip_path, pass_txt_path):
    try:
        with zipfile.ZipFile(zip_path) as zf, open(pass_txt_path, "r", encoding="utf-8") as pf:
            for pwd in pf.read().splitlines():
                try:
                    zf.extractall("downloads/unzipped", pwd=bytes(pwd, "utf-8"))
                    return f"Correct password is: {pwd} "
                except:
                    continue
        return "No matching password found."
    except Exception as e:
        return f"Error: {e}"

# Handle button
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "check_join":
        # Assume joined (real checking requires Telegram bot API group admin permissions)
        await query.edit_message_text(text=data["welcome"])
        data["user_state"][user_id] = {"stage": "awaiting_zip"}

# Handlers
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CommandHandler("add", add))
app.add_handler(CommandHandler("force", force))
app.add_handler(CommandHandler("welcome", welcome))
app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
app.add_handler(CallbackQueryHandler(handle_callback))

if __name__ == "__main__":
    print("Bot running...")
    app.run_polling()
