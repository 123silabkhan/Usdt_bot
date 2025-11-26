# usdt_bot.py
import os
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters, ConversationHandler
)

# ========================
# ENVIRONMENT VARIABLES
# ========================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = 6491173992  # Your admin ID

# Commission rules
USD_TO_AFN = 66

# States
(
    LANG, MAIN_MENU, AMOUNT, SELLER_SELECT,
    WALLET_TYPE, WALLET_INPUT, SCREENSHOT,
    REGISTER_NAME, REGISTER_WHATSAPP, REGISTER_HESABPAY,
    REGISTER_AMOUNT, REGISTER_RATE, REGISTER_METHODS
) = range(13)

# Temporary storage
user_data_store = {}
approved_sellers = {}
pending_sellers = {}

# ========================
# MULTI-LANGUAGE TEXT
# ========================
MSG = {
    "menu": {
        "en": "Main Menu:\nChoose an option:",
        "ps": "اصلي مینو:\nيو اختيار وټاکئ:",
        "fa": "منوی اصلی:\nیک گزینه را انتخاب کنید:"
    },
    "buttons": {
        "en": ["Buy USDT", "Become a Seller"],
        "ps": ["USDT اخیستل", "پلورنکی شئ"],
        "fa": ["خرید USDT", "فروشنده شوید"]
    },
    "start": {
        "en": "Welcome!\nChoose your language:",
        "ps": "ښه راغلاست!\nځان لپاره ژبه وټاکئ:",
        "fa": "خوش آمدید!\nلطفاً زبان را انتخاب کنید:"
    },
    "ask_amount": {
        "en": "How much USDT do you want to buy?",
        "ps": "تاسو څومره USDT اخیستل غواړئ؟",
        "fa": "چقدر USDT می‌خواهید بخرید؟"
    },
    "seller_select": {
        "en": "Choose a seller:",
        "ps": "پلورنکی انتخاب کړئ:",
        "fa": "فروشنده را انتخاب کنید:"
    },
    "wallet_method": {
        "en": "Choose your receiving method:",
        "ps": "د ترلاسه کولو طریقه وټاکئ:",
        "fa": "روش دریافت را انتخاب کنید:"
    },
    "wallet_input": {
        "en": "Enter your wallet details:",
        "ps": "د خپل والټ معلومات دننه کړئ:",
        "fa": "اطلاعات کیف پول خود را وارد کنید:"
    },
    "screenshot": {
        "en": "Upload your payment screenshot:",
        "ps": "ستاسو د تادیې سکرین شاټ اپلوډ کړئ:",
        "fa": "اسکرین‌شات پرداخت را ارسال کنید:"
    },
    "order_sent": {
        "en": "Your order has been sent to admin.",
        "ps": "ستاسو فرمایش مدیر ته ولېږل شو.",
        "fa": "سفارش شما به مدیر ارسال شد."
    },
    "seller_register": {
        "en": "Please enter your full name:",
        "ps": "مهرباني وکړئ خپل بشپړ نوم دننه کړئ:",
        "fa": "لطفاً نام کامل خود را وارد کنید:"
    },
}

# ========================
# START
# ========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["English", "Pashto", "Dari"]]
    reply = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(MSG["start"]["en"], reply_markup=reply)
    return LANG

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.lower()
    if "english" in txt: lang = "en"
    elif "pashto" in txt: lang = "ps"
    else: lang = "fa"

    user_data_store[update.message.from_user.id] = {"lang": lang}

    btns = MSG["buttons"][lang]
    reply = ReplyKeyboardMarkup([[btns[0]], [btns[1]]], resize_keyboard=True)
    await update.message.reply_text(MSG["menu"][lang], reply_markup=reply)
    return MAIN_MENU

# ========================
# MAIN MENU ACTIONS
# ========================
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    lang = user_data_store[user_id]["lang"]
    choice = update.message.text

    if choice in MSG["buttons"]["en"] or choice in MSG["buttons"]["ps"] or choice in MSG["buttons"]["fa"]:
        if choice in ["Buy USDT", "USDT اخیستل", "خرید USDT"]:
            return await buy_usdt_start(update, context)
        else:
            return await seller_register_start(update, context)

# ========================
# BUY USDT
# ========================
async def buy_usdt_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    lang = user_data_store[user_id]["lang"]

    if not approved_sellers:
        await update.message.reply_text("❌ No sellers available now.")
        return MAIN_MENU

    seller_buttons = [[name] for name in approved_sellers]
    reply = ReplyKeyboardMarkup(seller_buttons, resize_keyboard=True)

    await update.message.reply_text(MSG["seller_select"][lang], reply_markup=reply)
    return SELLER_SELECT

async def seller_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    seller = update.message.text
    user_id = update.message.from_user.id
    lang = user_data_store[user_id]["lang"]

    if seller not in approved_sellers:
        await update.message.reply_text("Invalid seller.")
        return MAIN_MENU

    user_data_store[user_id]["seller"] = seller
    await update.message.reply_text(MSG["ask_amount"][lang])
    return AMOUNT

async def enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    lang = user_data_store[user_id]["lang"]

    try:
        amount = float(update.message.text)
    except:
        await update.message.reply_text(MSG["ask_amount"][lang])
        return AMOUNT

    # COMMISSION
    if 1 <= amount <= 100:
        commission = 1
    else:
        commission = amount * 0.01

    total = amount + commission

    user_data_store[user_id]["amount"] = amount
    user_data_store[user_id]["commission"] = commission
    user_data_store[user_id]["total"] = total

    methods = ["Binance ID", "Bybit ID", "TRC20 Wallet", "All Options"]
    reply = ReplyKeyboardMarkup([[m] for m in methods], resize_keyboard=True)

    await update.message.reply_text(MSG["wallet_method"][lang], reply_markup=reply)
    return WALLET_TYPE

async def wallet_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    lang = user_data_store[user_id]["lang"]

    method = update.message.text
    user_data_store[user_id]["method"] = method

    await update.message.reply_text(MSG["wallet_input"][lang])
    return WALLET_INPUT

async def wallet_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    lang = user_data_store[user_id]["lang"]

    user_data_store[user_id]["wallet"] = update.message.text

    await update.message.reply_text(MSG["screenshot"][lang])
    return SCREENSHOT

async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    lang = user_data_store[user_id]["lang"]

    if not update.message.photo:
        await update.message.reply_text(MSG["screenshot"][lang])
        return SCREENSHOT

    file_id = update.message.photo[-1].file_id
    order = user_data_store[user_id]

    caption = (
        f"📩 New Order\n"
        f"User: @{update.message.from_user.username}\n"
        f"Seller: {order['seller']}\n"
        f"Amount: {order['amount']} USDT\n"
        f"Commission: {order['commission']}\n"
        f"Total: {order['total']}\n"
        f"Method: {order['method']}\n"
        f"Wallet: {order['wallet']}"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve", callback_data=f"done_{user_id}")],
        [InlineKeyboardButton("❌ Reject", callback_data=f"cancel_{user_id}")]
    ])

    await context.bot.send_photo(ADMIN_ID, file_id, caption=caption, reply_markup=keyboard)
    await update.message.reply_text(MSG["order_sent"][lang])
    return ConversationHandler.END

# ========================
# SELLER REGISTRATION
# ========================
async def seller_register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    lang = user_data_store[user_id]["lang"]

    await update.message.reply_text(MSG["seller_register"][lang])
    return REGISTER_NAME

async def seller_register_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    user_data_store[uid]["reg_name"] = update.message.text
    await update.message.reply_text("Enter WhatsApp number:")
    return REGISTER_WHATSAPP

async def seller_register_whatsapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    user_data_store[uid]["reg_whatsapp"] = update.message.text
    await update.message.reply_text("Enter HesabPay ID:")
    return REGISTER_HESABPAY

async def seller_register_hesab(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    user_data_store[uid]["reg_hesab"] = update.message.text
    await update.message.reply_text("How much USDT do you want to sell?")
    return REGISTER_AMOUNT

async def seller_register_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    user_data_store[uid]["reg_amount"] = update.message.text
    await update.message.reply_text("What is your selling rate?")
    return REGISTER_RATE

async def seller_register_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    user_data_store[uid]["reg_rate"] = update.message.text

    methods = ["Binance ID", "Bybit ID", "TRC20 Wallet", "All Options"]
    reply = ReplyKeyboardMarkup([[m] for m in methods], resize_keyboard=True)

    await update.message.reply_text("Choose your delivery method:", reply_markup=reply)
    return REGISTER_METHODS

async def seller_register_methods(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    method = update.message.text

    pending_sellers[uid] = {
        "name": user_data_store[uid]["reg_name"],
        "wa": user_data_store[uid]["reg_whatsapp"],
        "hesab": user_data_store[uid]["reg_hesab"],
        "amount": user_data_store[uid]["reg_amount"],
        "rate": user_data_store[uid]["reg_rate"],
        "method": method
    }

    caption = (
        f"📦 New Seller Request\n"
        f"Name: {pending_sellers[uid]['name']}\n"
        f"WhatsApp: {pending_sellers[uid]['wa']}\n"
        f"HesabPay: {pending_sellers[uid]['hesab']}\n"
        f"Amount: {pending_sellers[uid]['amount']}\n"
        f"Rate: {pending_sellers[uid]['rate']}\n"
        f"Method: {method}"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve", callback_data=f"seller_ok_{uid}")],
        [InlineKeyboardButton("❌ Reject", callback_data=f"seller_no_{uid}")]
    ])

    await context.bot.send_message(ADMIN_ID, caption, reply_markup=keyboard)
    await update.message.reply_text("Your seller request was submitted.")
    return ConversationHandler.END

# ========================
# ADMIN CALLBACKS
# ========================
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data

    # Order approval
    if data.startswith("done_"):
        uid = int(data.split("_")[1])
        lang = user_data_store.get(uid, {}).get("lang", "en")
        await context.bot.send_message(uid, "✅ Your order was approved.")
        await q.edit_message_caption("Order marked as approved.")
        return

    if data.startswith("cancel_"):
        uid = int(data.split("_")[1])
        lang = user_data_store.get(uid, {}).get("lang", "en")
        await context.bot.send_message(uid, "❌ Your order was rejected.")
        await q.edit_message_caption("Order rejected.")
        return

    # Seller approval
    if data.startswith("seller_ok_"):
        uid = int(data.split("_")[2])
        approved_sellers[pending_sellers[uid]["name"]] = pending_sellers[uid]
        del pending_sellers[uid]
        await q.edit_message_text("Seller approved!")
        return

    if data.startswith("seller_no_"):
        uid = int(data.split("_")[2])
        del pending_sellers[uid]
        await q.edit_message_text("Seller rejected.")
        return

# ========================
# CANCEL
# ========================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END

# ========================
# MAIN
# ========================
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG: [MessageHandler(filters.TEXT, set_language)],
            MAIN_MENU: [MessageHandler(filters.TEXT, main_menu)],
            SELLER_SELECT: [MessageHandler(filters.TEXT, seller_selected)],
            AMOUNT: [MessageHandler(filters.TEXT, enter_amount)],
            WALLET_TYPE: [MessageHandler(filters.TEXT, wallet_type)],
            WALLET_INPUT: [MessageHandler(filters.TEXT, wallet_input)],
            SCREENSHOT: [MessageHandler(filters.PHOTO, screenshot)],
            REGISTER_NAME: [MessageHandler(filters.TEXT, seller_register_name)],
            REGISTER_WHATSAPP: [MessageHandler(filters.TEXT, seller_register_whatsapp)],
            REGISTER_HESABPAY: [MessageHandler(filters.TEXT, seller_register_hesab)],
            REGISTER_AMOUNT: [MessageHandler(filters.TEXT, seller_register_amount)],
            REGISTER_RATE: [MessageHandler(filters.TEXT, seller_register_rate)],
            REGISTER_METHODS: [MessageHandler(filters.TEXT, seller_register_methods)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(admin_action))

    print("Bot running…")
    app.run_polling()

if __name__ == "__main__":
    main()
