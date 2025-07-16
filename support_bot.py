import warnings
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from telegram.warnings import PTBUserWarning

warnings.filterwarnings("ignore", category=PTBUserWarning)

TOKEN = "YOUR_BOT_TOKEN"
ADMIN1 = CHANGE_TO_YOUR_ADMIN_ID
ADMIN2 =  CHANGE_TO_YOUR_ADMIN_ID
ADMINS = {ADMIN1, ADMIN2}
BLOCKED = set()

MAIN_MENU, AWAITING_DETAILS = range(2)

app = Application.builder().token(TOKEN).build()

# ---------- handlers ----------
#start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    if uid in ADMINS:
        await update.message.reply_text("👨‍💻 Whait for the application")
        return ConversationHandler.END
    kb = [[InlineKeyboardButton("🤝 Cooperation", callback_data="c"),
           InlineKeyboardButton("🛠 Technical support",  callback_data="t")]]
    await update.message.reply_text("🔍 Choose type:", reply_markup=InlineKeyboardMarkup(kb))
    return MAIN_MENU
#?
async def pick_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    context.user_data["admin"] = ADMIN1 if q.data == "c" else ADMIN2
    await q.edit_message_text("✍️ Write your question:")
    return AWAITING_DETAILS
#admin panel 1
async def question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    admin = context.user_data["admin"]
    req = f"{user.id}-{admin}"
    kb = [[InlineKeyboardButton("✅ Confrim", callback_data=f"a_{req}"),
           InlineKeyboardButton("❌ Reject", callback_data=f"r_{req}")]]
    await context.bot.send_message(admin,
                                   f"📨 @{user.username or user.first_name}:\n\n{update.message.text}",
                                   reply_markup=InlineKeyboardMarkup(kb))
    context.bot_data[req] = user.id
    await update.message.reply_text("📩 Sended.")
    return ConversationHandler.END
#admin panel 2
async def admin_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    act, req = q.data.split("_", 1)
    user_id = context.bot_data.pop(req, None)
    if not user_id:
        return
    if act == "a":
        context.bot_data[f"chat_{req}"] = {"u": user_id, "a": q.from_user.id}
        await q.edit_message_text("✅ Confrim")
        await context.bot.send_message(user_id, "🎉 The admin accepted the application!")
    else:
        await q.edit_message_text("❌ rejected")
        await context.bot.send_message(user_id, "😞 The admin rejected the application..")
        if update.effective_user.id in BLOCKED:
            return

        
#fwd
async def fwd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    for k, v in context.bot_data.items():
        if k.startswith("chat_"):
            if v["u"] == uid:
                await context.bot.send_message(v["a"], update.message.text)
            elif v["a"] == uid:
                await context.bot.send_message(v["u"], update.message.text)
#stop chat
async def stop_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMINS:
        return
    for key, val in list(context.bot_data.items()):
        if key.startswith("chat_") and val["a"] == uid:
            await context.bot.send_message(val["u"], "🔚 The admin ended the chat.")
            del context.bot_data[key]
            await update.message.reply_text("✅ The chat is closed.")
            return
    await update.message.reply_text("ℹ️ there are no active chats.")

conv = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        MAIN_MENU: [CallbackQueryHandler(pick_type)],
        AWAITING_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, question)]
    },
    fallbacks=[CommandHandler('start', start)]
)

app.add_handler(conv)
app.add_handler(CommandHandler('stop_chat', stop_chat, filters.User(ADMINS)))
app.add_handler(CallbackQueryHandler(admin_choice, pattern="^[ar]_"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, fwd))

print("started")
app.run_polling()

