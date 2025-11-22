import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler
)

# Load environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 6491173992))
HESABPAY_ID = os.getenv("HESABPAY_ID", "0729376719")

# Conversation states
LANG, AMOUNT, WALLET, SCREENSHOT = range(4)

# Multi-language messages
MESSAGES = {
    "start": {
        "en": "Welcome! Please select your language:",
        "ps": "ښه راغلاست! مهرباني وکړئ خپله ژبه وټاکئ:",
        "fa": "خوش آمدید! لطفاً زبان خود را انتخاب کنید:"
    },
    "ask_amount": {
        "en": "Enter the amount of USDT you want to buy:",
        "ps": "هغه مقدار USDT داخل کړئ چې تاسو غواړئ واخلئ:",
        "fa": "مقدار USDT مورد نظر خود را وارد کنید:"
    },
    "ask_wallet": {
        "en": "Enter your Binance ID or TRC20 wallet address:",
        "ps": "خپل Binance ID یا TRC20 والټ داخل کړئ:",
        "fa": "شناسه Binance یا آدرس کیف پول TRC20 خود را وارد کنید:"
    },
    "payment_info": {
        "en": "Send {total} USD via HesabPay to ID: {hesabpay_id}",
        "ps": "{total} USD د HesabPay له لارې دې ID ته واستوئ: {hesabpay_id}",
        "fa": "{total} USD را از طریق HesabPay به این ID ارسال کنید: {hesabpay_id}"
    },
    "ask_screenshot": {
        "en": "Please upload your payment screenshot:",
        "ps": "مهرباني وکړئ د تادیې سکرین شاټ اپلوډ کړئ:",
        "fa": "لطفاً اسکرین شات پرداخت خود را ارسال کنید:"
    },
    "order_sent": {
        "en": "Your order has been sent to admin. Waiting for approval.",
        "ps": "ستاسو فرمایش مدیر ته لیږل شوی. د تصویب لپاره انتظار وکړئ.",
        "fa": "سفارش شما به مدیر ارسال شد. منتظر تایید باشید."
    }
}

# Store user data temporarily
user_data_store = {}

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("English"), KeyboardButton("Pashto"), KeyboardButton("Dari")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text(MESSAGES["start"]["en"], reply_markup=reply_markup)
    return LANG

# Language selection
async def select_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if "english" in text:
        lang = "en"
    elif "pashto" in text:
        lang = "ps"
    elif "dari" in text:
        lang = "fa"
    else:
        lang = "en"
    user_data_store[update.message.from_user.id] = {"lang": lang}
    await update.message.reply_text(MESSAGES["ask_amount"][lang])
    return AMOUNT

# Amount handler
async def enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    lang = user_data_store[user_id]["lang"]
    try:
        amount = float(update.message.text)
    except:
        await update.message.reply_text(MESSAGES["ask_amount"][lang])
        return AMOUNT

    # Commission calculation
    if 1 <= amount <= 100:
        commission = 3
    else:
        commission = amount * 0.04
    total = amount + commission

    user_data_store[user_id]["amount"] = amount
    user_data_store[user_id]["commission"] = commission
    user_data_store[user_id]["total"] = total

    await update.message.reply_text(MESSAGES["ask_wallet"][lang])
    return WALLET

# Wallet handler
async def enter_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    wallet = update.message.text
    user_data_store[user_id]["wallet"] = wallet
    lang = user_data_store[user_id]["lang"]

    await update.message.reply_text(
        MESSAGES["payment_info"][lang].format(
            total=user_data_store[user_id]["total"],
            hesabpay_id=HESABPAY_ID
        )
    )
    await update.message.reply_text(MESSAGES["ask_screenshot"][lang])
    return SCREENSHOT

# Screenshot handler
async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not update.message.photo:
        lang = user_data_store[user_id]["lang"]
        await update.message.reply_text(MESSAGES["ask_screenshot"][lang])
        return SCREENSHOT

    file_id = update.message.photo[-1].file_id
    user_data_store[user_id]["screenshot"] = file_id
    lang = user_data_store[user_id]["lang"]

    order = user_data_store[user_id]
    message = (
        f"New USDT Order\n"
        f"User: @{update.message.from_user.username}\n"
        f"Amount: {order['amount']} USDT\n"
        f"Commission: {order['commission']} USD\n"
        f"Total: {order['total']} USD\n"
        f"Wallet: {order['wallet']}"
    )
    await context.bot.send_photo(chat_id=ADMIN_ID, photo=file_id, caption=message)
    await update.message.reply_text(MESSAGES["order_sent"][lang])
    return ConversationHandler.END

# Cancel handler
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Order cancelled.")
    return ConversationHandler.END

# Main
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_language)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount)],
            WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_wallet)],
            SCREENSHOT: [MessageHandler(filters.PHOTO, screenshot)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv_handler)
    app.run_polling()
