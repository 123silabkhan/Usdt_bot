import os
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters
)

# Load environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 6491173992))
HESABPAY_ID = os.getenv("HESABPAY_ID", "0729376719")

# Conversation states
LANG, AMOUNT, WALLET, SCREENSHOT = range(4)

USD_TO_AFN = 66  # Fixed rate

# Messages
MESSAGES = {
    "start": {
        "en": "Welcome! Please select your language:",
        "ps": "ښه راغلاست! مهرباني وکړئ خپله ژبه وټاکئ:",
        "fa": "خوش آمدید! لطفاً زبان خود را انتخاب کنید:"
    },
    "ask_amount": {
        "en": "Select an amount or type your custom USDT amount:",
        "ps": "یو مقدار وټاکئ یا خپل د USDT مقدار ولیکئ:",
        "fa": "یک مقدار را انتخاب کنید یا مقدار دلخواه USDT را وارد کنید:"
    },
    "ask_wallet": {
        "en": "Choose one option:",
        "ps": "یو اختیار وټاکئ:",
        "fa": "یک گزینه را انتخاب کنید:"
    },
    "payment_info_enhanced": {
        "en": (
            "💵 *Payment Instructions*\n"
            "----------------------------\n"
            "• *Total Amount:* {usd:.2f} USD\n"
            "• *AFN Equivalent:* {afn:.2f} AFN\n"
            "• *Rate:* 66 AFN per 1 USD\n"
            "----------------------------\n\n"
            "📤 *Please send payment via HesabPay*\n"
            "➡️ *HesabPay ID:* `{hesab}`\n\n"
            "🖼 Upload your payment screenshot here after sending."
        ),
        "ps": (
            "💵 *د تادیې لارښود*\n"
            "----------------------------\n"
            "• *ټول مبلغ:* {usd:.2f} USD\n"
            "• *په افغانی کې:* {afn:.2f} AFN\n"
            "• *نرخ:* 66 AFN د 1 USD په مقابل کې\n"
            "----------------------------\n\n"
            "📤 *مهرباني وکړئ تادیه د HesabPay له لارې وکړئ*\n"
            "➡️ *HesabPay ID:* `{hesab}`\n\n"
            "🖼 وروسته د تادیې سکرین شاټ دلته اپلوډ کړئ."
        ),
        "fa": (
            "💵 *راهنمای پرداخت*\n"
            "----------------------------\n"
            "• *مبلغ کل:* {usd:.2f} USD\n"
            "• *معادل افغانی:* {afn:.2f} AFN\n"
            "• *نرخ:* هر 1 USD = 66 AFN\n"
            "----------------------------\n\n"
            "📤 *لطفاً پرداخت را از طریق HesabPay انجام دهید*\n"
            "➡️ *ID HesabPay:* `{hesab}`\n\n"
            "🖼 پس از پرداخت، اسکرین‌شات را ارسال کنید."
        )
    },
    "ask_screenshot": {
        "en": "Upload your payment screenshot:",
        "ps": "د تادیې سکرین شاټ اپلوډ کړئ:",
        "fa": "اسکرین‌شات پرداخت را ارسال کنید:"
    },
    "order_sent": {
        "en": "Your order has been sent to admin. Please wait for approval.",
        "ps": "ستاسو فرمایش مدیر ته ولېږل شو. مهرباني وکړئ انتظار وباسئ.",
        "fa": "سفارش شما به مدیر ارسال شد. لطفاً منتظر تأیید باشید."
    }
}

# Store user data
user_data_store = {}

# Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("English"), KeyboardButton("Pashto"), KeyboardButton("Dari")]]
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

    # USDT amount quick buttons
    amount_buttons = [
        ["10", "20", "30", "40", "50"],
        ["60", "70", "80", "90", "100"],
    ]

    reply_markup = ReplyKeyboardMarkup(amount_buttons, one_time_keyboard=True)

    await update.message.reply_text(MESSAGES["ask_amount"][lang], reply_markup=reply_markup)
    return AMOUNT

# Amount selection
async def enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    lang = user_data_store[user_id]["lang"]

    try:
        amount = float(update.message.text)
    except:
        await update.message.reply_text(MESSAGES["ask_amount"][lang])
        return AMOUNT

    # Commission rules
    if 1 <= amount <= 100:
        commission = 3
    else:
        commission = amount * 0.04

    total_usd = amount + commission
    total_afn = total_usd * USD_TO_AFN

    user_data_store[user_id].update({
        "amount": amount,
        "commission": commission,
        "total_usd": total_usd,
        "total_afn": total_afn
    })

    # Wallet menu
    keyboard = [
        [KeyboardButton("Binance ID"), KeyboardButton("TRC20 Wallet")],
        [KeyboardButton("Back")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    await update.message.reply_text(MESSAGES["ask_wallet"][lang], reply_markup=reply_markup)
    return WALLET

# Wallet handler
async def enter_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    choice = update.message.text
    lang = user_data_store[user_id]["lang"]

    user_data_store[user_id]["wallet"] = choice

    msg = MESSAGES["payment_info_enhanced"][lang].format(
        usd=user_data_store[user_id]["total_usd"],
        afn=user_data_store[user_id]["total_afn"],
        hesab=HESABPAY_ID
    )

    await update.message.reply_text(msg, parse_mode="Markdown")
    await update.message.reply_text(MESSAGES["ask_screenshot"][lang])
    return SCREENSHOT

# Screenshot
async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if not update.message.photo:
        lang = user_data_store[user_id]["lang"]
        await update.message.reply_text(MESSAGES["ask_screenshot"][lang])
        return SCREENSHOT

    file_id = update.message.photo[-1].file_id
    data = user_data_store[user_id]

    caption = (
        f"📦 *New USDT Order*\n"
        f"---------------------------\n"
        f"👤 User: @{update.message.from_user.username}\n"
        f"💰 Amount: {data['amount']} USDT\n"
        f"📌 Commission: {data['commission']} USD\n"
        f"💵 Total: {data['total_usd']} USD\n"
        f"🇦🇫 AFN: {data['total_afn']:.2f}\n"
        f"🏦 Wallet: {data['wallet']}"
    )

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=file_id,
        caption=caption,
        parse_mode="Markdown"
    )

    lang = user_data_store[user_id]["lang"]
    await update.message.reply_text(MESSAGES["order_sent"][lang])
    return ConversationHandler.END

# Cancel
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
            SCREENSHOT: [MessageHandler(filters.PHOTO, screenshot)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv_handler)
    app.run_polling()
