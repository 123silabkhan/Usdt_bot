import os
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters, ConversationHandler
)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6491173992"))
HESABPAY_ID = os.getenv("HESABPAY_ID", "0729376719")

AFN_RATE = 66  # Default

LANG, AMOUNT, WALLET_TYPE, WALLET_INPUT, SCREENSHOT = range(5)

MESSAGES = {
    "start": {
        "en": "Welcome!\n\nPlease select your language:",
        "ps": "ښه راغلاست!\n\nمهرباني وکړئ خپله ژبه وټاکئ:",
        "fa": "خوش آمدید!\n\nلطفاً زبان خود را انتخاب کنید:"
    },
    "ask_amount": {
        "en": "How much USDT do you want to buy?\n\nChoose an amount or type a custom one:",
        "ps": "تاسو څومره USDT اخیستل غواړئ؟\n\nلاندې اندازه وټاکئ یا خپله اندازه ولیکئ:",
        "fa": "چقدر USDT می‌خواهید خریداری کنید؟\n\nیک مقدار انتخاب کنید یا مقدار دلخواه را بنویسید:"
    },
    "ask_wallet_type": {
        "en": "Choose your receiving method:",
        "ps": "خپل د ترلاسه کولو طریقه وټاکئ:",
        "fa": "روش دریافت خود را انتخاب کنید:"
    },
    "ask_wallet_input": {
        "en": "Please enter your wallet details:",
        "ps": "مهرباني وکړئ د خپل والټ معلومات داخل کړئ:",
        "fa": "لطفاً اطلاعات کیف پول خود را وارد کنید:"
    },
    "payment_info": {
        "en": (
            "✅ *Payment Details*\n\n"
            "• Total USD: *{total}*\n"
            "• Total AFN: *{total_afn} AFN*\n\n"
            "👉 Send the amount via *HesabPay* to this ID:\n"
            "*{hesabpay}*\n\n"
            "After sending, upload your screenshot below:"
        ),
        "ps": (
            "✅ *د تادیې معلومات*\n\n"
            "• مجموعي USD: *{total}*\n"
            "• مجموعي AFN: *{total_afn} افغانۍ*\n\n"
            "👉 مهرباني وکړئ پیسې د *HesabPay* له لارې دې ID ته واستوئ:\n"
            "*{hesabpay}*\n\n"
            "له لېږلو وروسته، خپل سکرین شاټ دلته اپلوډ کړئ:"
        ),
        "fa": (
            "✅ *جزئیات پرداخت*\n\n"
            "• مجموع USD: *{total}*\n"
            "• مجموع AFN: *{total_afن} افغانی*\n\n"
            "👉 لطفاً مبلغ را از طریق *حساب‌پی* به این آی‌دی ارسال کنید:\n"
            "*{hesabpay}*\n\n"
            "بعد از ارسال، اسکرین‌شات پرداخت را آپلود کنید:"
        )
    },
    "ask_screenshot": {
        "en": "Upload your payment screenshot:",
        "ps": "مهرباني وکړئ د تادیې سکرین شاټ اپلوډ کړئ:",
        "fa": "لطفاً اسکرین‌شات پرداخت خود را آپلود کنید:"
    },
    "order_sent": {
        "en": "Your order has been sent to admin. Please wait for approval.",
        "ps": "ستاسو فرمایش مدیر ته ولېږل شو. مهرباني وکړئ د تایید لپاره انتظار وکړئ.",
        "fa": "سفارش شما برای مدیر ارسال شد. لطفاً منتظر تایید باشید."
    },
    "approved_user": {
        "en": "✅ Your USDT has been delivered successfully!",
        "ps": "✅ ستاسو USDT په بریالیتوب سره درولیږل شو!",
        "fa": "✅ تتر شما با موفقیت ارسال شد!"
    },
    "rejected_user": {
        "en": "❌ Your order was rejected by admin.",
        "ps": "❌ ستاسو فرمایش د مدیر لخوا رد شو.",
        "fa": "❌ سفارش شما توسط مدیر رد شد."
    }
}

user_data_store = {}

# -------- START -------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("English"), KeyboardButton("Pashto"), KeyboardButton("Dari")]]
    reply = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(MESSAGES["start"]["en"], reply_markup=reply)
    return LANG

async def select_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.lower()
    lang = "en" if "english" in txt else "ps" if "pashto" in txt else "fa"

    user_data_store[update.message.from_user.id] = {"lang": lang}

    buttons = [
        ["10", "20", "30", "40", "50"],
        ["60", "70", "80", "90", "100"],
        ["Custom Amount"]
    ]
    reply = ReplyKeyboardMarkup(buttons, resize_keyboard=True)

    await update.message.reply_text(MESSAGES["ask_amount"][lang], reply_markup=reply)
    return AMOUNT

async def enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    lang = user_data_store[user_id]["lang"]

    txt = update.message.text

    if txt.lower() == "custom amount":
        msg = "Enter custom USDT amount:" if lang == "en" else \
              "خپل مقدار داخل کړئ:" if lang == "ps" else \
              "مقدار مورد نظر را وارد کنید:"
        await update.message.reply_text(msg)
        return AMOUNT

    try:
        amount = float(txt)
    except:
        await update.message.reply_text(MESSAGES["ask_amount"][lang])
        return AMOUNT

    commission = 3 if amount <= 100 else amount * 0.04
    total = round(amount + commission, 2)
    total_afn = round(total * AFN_RATE, 2)

    user_data_store[user_id]["amount"] = amount
    user_data_store[user_id]["total"] = total
    user_data_store[user_id]["total_afn"] = total_afn

    keyboard = [["Binance ID", "TRC20 Address"]]
    reply = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(MESSAGES["ask_wallet_type"][lang], reply_markup=reply)
    return WALLET_TYPE

async def choose_wallet_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data_store[user_id]["wallet_type"] = update.message.text
    lang = user_data_store[user_id]["lang"]

    await update.message.reply_text(MESSAGES["ask_wallet_input"][lang])
    return WALLET_INPUT

async def wallet_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    wallet = update.message.text
    lang = user_data_store[user_id]["lang"]

    user_data_store[user_id]["wallet"] = wallet
    total = user_data_store[user_id]["total"]
    total_afn = user_data_store[user_id]["total_afn"]

    msg = MESSAGES["payment_info"][lang].format(
        total=total, total_afn=total_afn, hesabpay=HESABPAY_ID
    )

    await update.message.reply_text(msg, parse_mode="Markdown")
    await update.message.reply_text(MESSAGES["ask_screenshot"][lang])
    return SCREENSHOT

async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    lang = user_data_store[user_id]["lang"]

    if not update.message.photo:
        await update.message.reply_text(MESSAGES["ask_screenshot"][lang])
        return SCREENSHOT

    file_id = update.message.photo[-1].file_id
    user_data_store[user_id]["screenshot"] = file_id

    order = user_data_store[user_id]

    caption = (
        f"📩 *New USDT Order*\n\n"
        f"👤 User: @{update.message.from_user.username}\n"
        f"💵 Amount: {order['amount']} USDT\n"
        f"💰 Total: {order['total']} USD ({order['total_afn']} AFN)\n"
        f"🏦 Wallet: {order['wallet']}"
    )

    buttons = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve:{user_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject:{user_id}")
        ]
    ]

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=file_id,
        caption=caption,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

    await update.message.reply_text(MESSAGES["order_sent"][lang])
    return ConversationHandler.END

# -------- ADMIN CALLBACK -------- #

async def admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, user_id = query.data.split(":")
    user_id = int(user_id)

    lang = user_data_store[user_id]["lang"]

    if action == "approve":
        await context.bot.send_message(chat_id=user_id, text=MESSAGES["approved_user"][lang])
        await query.edit_message_caption(query.message.caption + "\n\n✅ Approved")

    else:
        await context.bot.send_message(chat_id=user_id, text=MESSAGES["rejected_user"][lang])
        await query.edit_message_caption(query.message.caption + "\n\n❌ Rejected")

# -------- RATE SETTER -------- #

async def rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global AFN_RATE
    if update.message.from_user.id != ADMIN_ID:
        return

    try:
        AFN_RATE = float(context.args[0])
        await update.message.reply_text(f"Rate updated to {AFN_RATE}")
    except:
        await update.message.reply_text("Usage: /rate 67")

# -------- MAIN -------- #

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_language)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount)],
            WALLET_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_wallet_pype)],
            WALLET_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_input)],
            SCREENSHOT: [MessageHandler(filters.PHOTO, screenshot)],
        },
        fallbacks=[]
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(admin_actions))
    app.add_handler(CommandHandler("rate", rate))

    app.run_polling()

if __name__ == "__main__":
    main()
