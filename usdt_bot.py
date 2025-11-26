# usdt_bot.py

import os
import json
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters, ConversationHandler
)

# -----------------------------
# ENVIRONMENT (token added on Render)
# -----------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = 6491173992  # Your admin ID

# -----------------------------
# JSON STORAGE
# -----------------------------
SELLERS_FILE = "sellers.json"
ORDERS_FILE = "orders.json"

def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

sellers = load_json(SELLERS_FILE)         # {user_id: {...}}
sell_orders = load_json(ORDERS_FILE)      # {seller_id: {...}}

# -----------------------------
# BOT STATES
# -----------------------------
(
    LANG,
    HOME,
    BUY_AMOUNT,
    BUY_WALLET_TYPE,
    BUY_WALLET_INPUT,
    BUY_SCREENSHOT,
    SELLER_NAME,
    SELLER_WHATSAPP,
    SELLER_HESABPAY,
    SELLER_WAIT_ADMIN,
    SELL_ORDER_AMOUNT,
    SELL_ORDER_RATE,
    SELL_ORDER_METHOD
) = range(13)

# -----------------------------
# MULTI-LANGUAGE MESSAGES
# -----------------------------
STR = {
    "welcome": {
        "en": "Welcome! Please select your language:",
        "ps": "ښه راغلاست! مهرباني وکړئ خپله ژبه وټاکئ:",
        "fa": "خوش آمدید! لطفاً زبان خود را انتخاب کنید:"
    },

    "menu": {
        "en": "🏠 *Main Menu*\nChoose an option:",
        "ps": "🏠 *اصلي مېنو*\nیوه برخه وټاکئ:",
        "fa": "🏠 *منوی اصلی*\nیک گزینه را انتخاب کنید:"
    },

    "btn_buy": {
        "en": "Buy USDT",
        "ps": "USDT اخیستل",
        "fa": "خرید USDT"
    },

    "btn_register_seller": {
        "en": "Register as Seller",
        "ps": "راجستر د خرڅوونکي په توګه",
        "fa": "ثبت فروشنده"
    },

    "btn_create_sell_order": {
        "en": "Create Sell Order",
        "ps": "د پلور امر جوړ کړئ",
        "fa": "ایجاد سفارش فروش"
    },

    "seller_reg_name": {
        "en": "Enter your full name:",
        "ps": "خپل بشپړ نوم ولیکئ:",
        "fa": "نام کامل خود را وارد کنید:"
    },

    "seller_reg_whatsapp": {
        "en": "Enter your WhatsApp number:",
        "ps": "خپل واټس اپ نمبر ولیکئ:",
        "fa": "شماره واتس‌اپ خود را وارد کنید:"
    },

    "seller_reg_hesabpay": {
        "en": "Enter your HesabPay ID:",
        "ps": "خپل HesabPay ID ولیکئ:",
        "fa": "شناسه HesabPay خود را وارد کنید:"
    },

    "seller_wait": {
        "en": "Your registration has been sent to admin. Please wait for approval.",
        "ps": "ستاسو رجسټریشن مدیر ته ولېږل شو. د تایید لپاره انتظار وکړئ.",
        "fa": "ثبت‌نام شما برای مدیر ارسال شد. لطفاً منتظر تایید باشید."
    },

    "seller_approved": {
        "en": "🎉 You are now an approved seller! You can create sell orders.",
        "ps": "🎉 تاسو اوس منظور شوی خرڅوونکي یاست! تاسو کولی شئ د پلور امر جوړ کړئ.",
        "fa": "🎉 شما اکنون یک فروشنده تاییدشده هستید! می‌توانید سفارش فروش ایجاد کنید."
    },

    "seller_rejected": {
        "en": "❌ Your seller registration was rejected by admin.",
        "ps": "❌ ستاسو د خرڅوونکي رجسټریشن رد شو.",
        "fa": "❌ ثبت‌نام فروشندگی شما رد شد."
    },

    "sell_amount": {
        "en": "How many USDT do you want to sell?",
        "ps": "تاسو څومره USDT پلورل غواړئ؟",
        "fa": "چقدر USDT می‌خواهید بفروشید؟"
    },

    "sell_rate": {
        "en": "Enter your selling rate (AFN per USDT):",
        "ps": "خپل د پلور نرخ داخل کړئ (AFN هر USDT):",
        "fa": "نرخ فروش خود را وارد کنید (افغانی برای هر USDT):"
    },

    "sell_method": {
        "en": "Choose your selling method:",
        "ps": "د پلور طریقه وټاکئ:",
        "fa": "روش فروش خود را انتخاب کنید:"
    },

    "sell_saved": {
        "en": "✅ Your sell order is now active!",
        "ps": "✅ ستاسو د پلور امر فعال شو!",
        "fa": "✅ سفارش فروش شما فعال شد!"
    },

    "buy_choose_seller": {
        "en": "Select a seller:",
        "ps": "یو خرڅوونکی وټاکئ:",
        "fa": "یک فروشنده را انتخاب کنید:"
    },

    "no_sellers": {
        "en": "❌ No active sellers available.",
        "ps": "❌ هیڅ فعال خرڅوونکی نشته.",
        "fa": "❌ هیچ فروشنده فعالی موجود نیست."
    }
}

# -----------------------------
# MAIN MENU
# -----------------------------
def main_menu(lang):
    return ReplyKeyboardMarkup([
        [STR["btn_buy"][lang]],
        [STR["btn_register_seller"][lang]],
        [STR["btn_create_sell_order"][lang]]
    ], resize_keyboard=True)

# -----------------------------
# /start
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = ReplyKeyboardMarkup([
        ["English", "Pashto", "Dari"]
    ], resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text(STR["welcome"]["en"], reply_markup=kb)
    return LANG

# -----------------------------
# LANGUAGE SELECT
# -----------------------------
async def select_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.lower()
    if "english" in t: lang = "en"
    elif "pashto" in t: lang = "ps"
    else: lang = "fa"

    context.user_data["lang"] = lang

    await update.message.reply_text(
        STR["menu"][lang],
        reply_markup=main_menu(lang),
        parse_mode="Markdown"
    )
    return HOME

# ----------------------------------------------------
# HANDLE MAIN MENU BUTTONS
# ----------------------------------------------------
async def home_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "en")
    text = update.message.text

    if text == STR["btn_buy"][lang]:
        return await start_buy_flow(update, context)

    if text == STR["btn_register_seller"][lang]:
        return await seller_register_start(update, context)

    if text == STR["btn_create_sell_order"][lang]:
        user_id = update.message.from_user.id
        if str(user_id) not in sellers or not sellers[str(user_id)]["approved"]:
            await update.message.reply_text("❌ You are not an approved seller.")
            return HOME
        return await seller_create_order(update, context)

    await update.message.reply_text(STR["menu"][lang], reply_markup=main_menu(lang))
    return HOME

# ----------------------------------------------------
# BUY USDT FLOW (ASK SELLER SELECTION FIRST)
# ----------------------------------------------------
async def start_buy_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data["lang"]

    if len(sell_orders) == 0:
        await update.message.reply_text(STR["no_sellers"][lang])
        return HOME

    kb = []
    for sid, order in sell_orders.items():
        label = f"{order['name']} – {order['amount']} USDT – {order['rate']} AFN"
        kb.append([label])

    context.user_data["buy_select"] = True

    await update.message.reply_text(
        STR["buy_choose_seller"][lang],
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return BUY_AMOUNT

# ----------------------------------------------------
# BUY AMOUNT (CONTINUES INTO NORMAL PAYMENT FLOW)
# ----------------------------------------------------
async def buy_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data["lang"]

    text = update.message.text

    # Detect selected seller
    for sid, order in sell_orders.items():
        if order["name"] in text:
            context.user_data["buyer_seller_id"] = sid
            context.user_data["seller_info"] = order
            break

    await update.message.reply_text(
        "Enter amount you want to buy:",
        reply_markup=ReplyKeyboardMarkup([["Cancel"]], resize_keyboard=True)
    )
    return BUY_WALLET_TYPE

# ----------------------------------------------------
# WALLET TYPE
# ----------------------------------------------------
async def buy_wallet_type(update, context):
    lang = context.user_data["lang"]
    amount = update.message.text

    try:
        context.user_data["buy_amount"] = float(amount)
    except:
        await update.message.reply_text("Invalid amount.")
        return BUY_WALLET_TYPE

    kb = [["Binance ID", "Bybit ID"], ["TRC20", "All"]]
    await update.message.reply_text(
        "Choose payment method:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return BUY_WALLET_INPUT

# ----------------------------------------------------
# WALLET INPUT
# ----------------------------------------------------
async def buy_wallet_input(update, context):
    context.user_data["buy_method"] = update.message.text
    await update.message.reply_text("Enter your wallet address/ID:")
    return BUY_SCREENSHOT

# ----------------------------------------------------
# BUY SCREENSHOT
# ----------------------------------------------------
async def buy_screenshot(update, context):
    lang = context.user_data["lang"]

    if not update.message.photo:
        await update.message.reply_text("Send screenshot:")
        return BUY_SCREENSHOT

    buyer_id = update.message.from_user.id
    photo = update.message.photo[-1].file_id
    amount = context.user_data["buy_amount"]
    method = context.user_data["buy_method"]
    wallet = update.message.caption if update.message.caption else "N/A"
    seller = context.user_data["seller_info"]

    # SEND ORDER TO ADMIN
    caption = (
        f"📩 *BUY ORDER*\n"
        f"👤 Buyer: {buyer_id}\n"
        f"💰 Amount: {amount} USDT\n"
        f"🏦 Method: {method}\n"
        f"🔐 Wallet: {wallet}\n"
        f"🛒 Seller: {seller['name']}\n"
        f"📞 WhatsApp: {seller['whatsapp']}\n"
    )

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo,
        caption=caption,
        parse_mode="Markdown"
    )

    await update.message.reply_text("Your order has been sent to admin.")
    return HOME

# ----------------------------------------------------
# SELLER REGISTRATION
# ----------------------------------------------------
async def seller_register_start(update, context):
    lang = context.user_data["lang"]
    await update.message.reply_text(STR["seller_reg_name"][lang])
    return SELLER_NAME

async def seller_reg_name(update, context):
    context.user_data["seller_name"] = update.message.text
    lang = context.user_data["lang"]
    await update.message.reply_text(STR["seller_reg_whatsapp"][lang])
    return SELLER_WHATSAPP

async def seller_reg_whatsapp(update, context):
    context.user_data["seller_whatsapp"] = update.message.text
    lang = context.user_data["lang"]
    await update.message.reply_text(STR["seller_reg_hesabpay"][lang])
    return SELLER_HESABPAY

async def seller_reg_hesabpay(update, context):
    user_id = str(update.message.from_user.id)
    name = context.user_data["seller_name"]
    whatsapp = context.user_data["seller_whatsapp"]
    hesabpay = update.message.text

    sellers[user_id] = {
        "name": name,
        "whatsapp": whatsapp,
        "hesabpay": hesabpay,
        "approved": False
    }
    save_json(SELLERS_FILE, sellers)

    # SEND TO ADMIN FOR APPROVAL
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Approve", callback_data=f"approve_{user_id}")],
        [InlineKeyboardButton("Reject", callback_data=f"reject_{user_id}")]
    ])

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📩 *New Seller Registration*\n\n"
             f"👤 Name: {name}\n"
             f"📞 WhatsApp: {whatsapp}\n"
             f"🏦 HesabPay: {hesabpay}",
        parse_mode="Markdown",
        reply_markup=kb
    )

    lang = context.user_data["lang"]
    await update.message.reply_text(STR["seller_wait"][lang])
    return HOME

# ----------------------------------------------------
# ADMIN APPROVAL
# ----------------------------------------------------
async def admin_action(update, context):
    query = update.callback_query
    action, uid = query.data.split("_")

    if action == "approve":
        sellers[uid]["approved"] = True
        save_json(SELLERS_FILE, sellers)

        await context.bot.send_message(
            chat_id=int(uid),
            text=STR["seller_approved"][sellers[uid].get("lang", "en")]
        )

        await query.edit_message_text("Seller APPROVED.")
    else:
        sellers[uid]["approved"] = False
        save_json(SELLERS_FILE, sellers)

        await context.bot.send_message(
            chat_id=int(uid),
            text=STR["seller_rejected"][sellers[uid].get("lang", "en")]
        )

        await query.edit_message_text("Seller REJECTED.")

# ----------------------------------------------------
# SELL ORDER CREATION
# ----------------------------------------------------
async def seller_create_order(update, context):
    lang = context.user_data["lang"]
    await update.message.reply_text(STR["sell_amount"][lang])
    return SELL_ORDER_AMOUNT

async def sell_order_amount(update, context):
    try:
        amt = float(update.message.text)
    except:
        await update.message.reply_text("Invalid amount.")
        return SELL_ORDER_AMOUNT

    context.user_data["sell_amt"] = amt

    lang = context.user_data["lang"]
    await update.message.reply_text(STR["sell_rate"][lang])
    return SELL_ORDER_RATE

async def sell_order_rate(update, context):
    try:
        rate = float(update.message.text)
    except:
        await update.message.reply_text("Invalid rate.")
        return SELL_ORDER_RATE

    context.user_data["sell_rate"] = rate

    lang = context.user_data["lang"]

    kb = [["Binance", "Bybit"], ["TRC20", "All"]]
    await update.message.reply_text(
        STR["sell_method"][lang],
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

    return SELL_ORDER_METHOD

async def sell_order_method(update, context):
    method = update.message.text
    seller_id = str(update.message.from_user.id)

    name = sellers[seller_id]["name"]
    whatsapp = sellers[seller_id]["whatsapp"]
    amt = context.user_data["sell_amt"]
    rate = context.user_data["sell_rate"]

    sell_orders[seller_id] = {
        "name": name,
        "whatsapp": whatsapp,
        "amount": amt,
        "rate": rate,
        "method": method
    }
    save_json(ORDERS_FILE, sell_orders)

    lang = context.user_data["lang"]
    await update.message.reply_text(
        STR["sell_saved"][lang],
        reply_markup=main_menu(lang)
    )

    return HOME

# -----------------------------
# CANCEL
# -----------------------------
async def cancel(update, context):
    await update.message.reply_text("Cancelled.")
    return HOME

# -----------------------------
# MAIN ENTRY
# -----------------------------
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_language)],
            HOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, home_handler)],

            BUY_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, buy_amount)],
            BUY_WALLET_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, buy_wallet_type)],
            BUY_WALLET_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, buy_wallet_input)],
            BUY_SCREENSHOT: [MessageHandler(filters.PHOTO, buy_screenshot)],

            SELLER_NAME: [MessageHandler(filters.TEXT, seller_reg_name)],
            SELLER_WHATSAPP: [MessageHandler(filters.TEXT, seller_reg_whatsapp)],
            SELLER_HESABPAY: [MessageHandler(filters.TEXT, seller_reg_hesabpay)],

            SELL_ORDER_AMOUNT: [MessageHandler(filters.TEXT, sell_order_amount)],
            SELL_ORDER_RATE: [MessageHandler(filters.TEXT, sell_order_rate)],
            SELL_ORDER_METHOD: [MessageHandler(filters.TEXT, sell_order_method)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(admin_action))

    print("BOT RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()
