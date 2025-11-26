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

# -----------------------------
# ADMIN SETTINGS
# -----------------------------
ADMIN_ID = 6491173992   # Only YOU are admin

# -----------------------------
# CENTRAL PAYMENT DETAILS
# -----------------------------
PAYMENT_NAME = "Mooj E-sarafi"
PAYMENT_ID = "0729376719"

# -----------------------------
# STATES
# -----------------------------
(
    LANG, MAIN_MENU,
    SELLER_NAME, SELLER_PHONE, SELLER_HESAB, WAIT_ADMIN_APPROVAL,
    ORDER_AMOUNT, ORDER_COMMISSION_TYPE, ORDER_COMMISSION_VALUE, ORDER_WALLET,
    CUSTOMER_AMOUNT, CUSTOMER_WALLET, CUSTOMER_PAYMENT, CUSTOMER_SCREENSHOT
) = range(14)

# -----------------------------
# DB TEMP MEMORY
# -----------------------------
seller_db = {}
orders_db = {}
user_data_store = {}

# -----------------------------
# LANG TEXTS
# -----------------------------
MESSAGES = {
    "start": {
        "en": "Welcome! Choose your language:",
        "ps": "ښه راغلاست! خپله ژبه وټاکئ:",
        "fa": "خوش آمدید! زبان خود را انتخاب کنید:"
    },
    "main_menu": {
        "en": "Choose an option:",
        "ps": "یو انتخاب وټاکئ:",
        "fa": "یک گزینه را انتخاب کنید:"
    },
    "menu_buttons": {
        "en": ["Buy USDT", "Register as Seller"],
        "ps": ["USDT واخلئ", "پلورونکی ثبت کړئ"],
        "fa": ["خرید USDT", "ثبت‌نام فروشنده"]
    },
    "seller_register_name": {
        "en": "Enter your full name:",
        "ps": "خپل بشپړ نوم دننه کړئ:",
        "fa": "نام کامل خود را وارد کنید:"
    },
    "seller_register_phone": {
        "en": "Enter your WhatsApp number:",
        "ps": "خپل واټساپ شمېره ولیکئ:",
        "fa": "شماره واتس‌اپ خود را وارد کنید:"
    },
    "seller_register_hesab": {
        "en": "Enter your HesabPay ID:",
        "ps": "د خپل حساب‌پی آي ډي ولیکئ:",
        "fa": "شناسه HesabPay خود را وارد کنید:"
    },
    "seller_wait_admin": {
        "en": "Your registration is submitted. Wait for admin approval.",
        "ps": "ستاسې معلومات واستول شول. د اډمین تایید ته انتظار وباسئ.",
        "fa": "درخواست شما ارسال شد. منتظر تأیید ادمین باشید."
    }
}

# ============================================================
# /start RESET
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    user_id = update.message.from_user.id
    if user_id in user_data_store:
        del user_data_store[user_id]

    keyboard = [
        [KeyboardButton("English"), KeyboardButton("Pashto"), KeyboardButton("Dari")]
    ]
    reply = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text(
        MESSAGES["start"]["en"],
        reply_markup=reply
    )
    return LANG

# ============================================================
# LANGUAGE SELECTION
# ============================================================
async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text

    if txt == "English":
        lang = "en"
    elif txt == "Pashto":
        lang = "ps"
    else:
        lang = "fa"

    context.user_data["lang"] = lang

    kb = [[btn] for btn in MESSAGES["menu_buttons"][lang]]

    await update.message.reply_text(
        MESSAGES["main_menu"][lang],
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return MAIN_MENU

# ============================================================
# MAIN MENU
# ============================================================
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data["lang"]
    choice = update.message.text

    # BUY FLOW
    if choice == MESSAGES["menu_buttons"][lang][0]:
        await update.message.reply_text(
            "Enter amount of USDT:",
            reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)
        )
        return CUSTOMER_AMOUNT

    # SELLER REGISTRATION
    if choice == MESSAGES["menu_buttons"][lang][1]:
        await update.message.reply_text(
            MESSAGES["seller_register_name"][lang],
            reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)
        )
        return SELLER_NAME

# ============================================================
# SELLER REGISTRATION
# ============================================================
async def seller_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["seller_name"] = update.message.text
    lang = context.user_data["lang"]

    await update.message.reply_text(
        MESSAGES["seller_register_phone"][lang],
        reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)
    )
    return SELLER_PHONE

async def seller_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["seller_phone"] = update.message.text
    lang = context.user_data["lang"]

    await update.message.reply_text(
        MESSAGES["seller_register_hesab"][lang],
        reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)
    )
    return SELLER_HESAB

async def seller_hesab(update: Update, context: ContextTypes.DEFAULT_TYPE):
    seller_id = update.message.from_user.id
    lang = context.user_data["lang"]

    seller_db[seller_id] = {
        "name": context.user_data["seller_name"],
        "phone": context.user_data["seller_phone"],
        "hesab": update.message.text,
        "approved": False
    }

    await update.message.reply_text(
        MESSAGES["seller_wait_admin"][lang],
        reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)
    )

    # Send to Admin
    await context.bot.send_message(
        ADMIN_ID,
        f"NEW SELLER REQUEST:\n\n"
        f"Name: {seller_db[seller_id]['name']}\n"
        f"WhatsApp: {seller_db[seller_id]['phone']}\n"
        f"HesabPay: {seller_db[seller_id]['hesab']}\n\n"
        f"Approve Seller → /approve_{seller_id}"
    )

    return WAIT_ADMIN_APPROVAL

# ============================================================
# ADMIN APPROVES SELLER
# ============================================================
async def approve_seller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    text = update.message.text
    if not text.startswith("/approve_"):
        return

    seller_id = int(text.split("_")[1])
    if seller_id in seller_db:
        seller_db[seller_id]["approved"] = True

        await update.message.reply_text(f"Seller {seller_id} approved ✔")

        await context.bot.send_message(
            seller_id,
            "Your seller account is approved! You can now create orders."
        )

# ============================================================
# CUSTOMER BUY FLOW
# ============================================================
async def customer_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amt = float(update.message.text)
    context.user_data["buy_amount"] = amt

    await update.message.reply_text(
        "Enter your TRC20 wallet address:",
        reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)
    )
    return CUSTOMER_WALLET

async def customer_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["wallet"] = update.message.text

    amt = context.user_data["buy_amount"]

    # PLATFORM COMMISSION
    if amt <= 100:
        platform_fee = 1
    else:
        platform_fee = amt * 0.01

    total_pay = amt + platform_fee

    await update.message.reply_text(
        f"Platform fee: {platform_fee}$\n"
        f"Total you must pay: {total_pay}$\n\n"
        f"Send payment to:\n"
        f"Name: {PAYMENT_NAME}\n"
        f"HesabPay ID: {PAYMENT_ID}\n\n"
        f"Upload payment screenshot:",
        reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)
    )
    return CUSTOMER_SCREENSHOT

async def customer_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    amt = context.user_data["buy_amount"]
    wallet = context.user_data["wallet"]

    # Forward to admin
    await context.bot.send_photo(
        ADMIN_ID,
        update.message.photo[-1].file_id,
        caption=f"NEW ORDER:\nUser: {user_id}\nAmount: {amt}\nWallet: {wallet}\n\nApprove? /confirm_{user_id}"
    )

    await update.message.reply_text("Your order is submitted. Please wait for confirmation.")
    return ConversationHandler.END

# ============================================================
# ADMIN CONFIRMS PAYMENT
# ============================================================
async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    text = update.message.text
    if not text.startswith("/confirm_"):
        return

    user_id = int(text.split("_")[1])

    await context.bot.send_message(
        user_id,
        "Your payment is confirmed. Seller will send USDT shortly."
    )

# ============================================================
# RUN BOT
# ============================================================
def main():
    TOKEN = os.getenv("BOT_TOKEN")  # ADD TOKEN IN RENDER ENVIRONMENT
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={

            LANG: [MessageHandler(filters.TEXT, set_language)],

            MAIN_MENU: [MessageHandler(filters.TEXT, main_menu)],

            SELLER_NAME: [MessageHandler(filters.TEXT, seller_name)],
            SELLER_PHONE: [MessageHandler(filters.TEXT, seller_phone)],
            SELLER_HESAB: [MessageHandler(filters.TEXT, seller_hesab)],

            CUSTOMER_AMOUNT: [MessageHandler(filters.TEXT, customer_amount)],
            CUSTOMER_WALLET: [MessageHandler(filters.TEXT, customer_wallet)],
            CUSTOMER_SCREENSHOT: [MessageHandler(filters.PHOTO, customer_screenshot)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("approve", approve_seller))
    app.add_handler(MessageHandler(filters.TEXT, approve_seller))
    app.add_handler(MessageHandler(filters.TEXT, confirm_order))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
