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

# Load environment variables (PythonAnywhere compatible)
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
HESABPAY_ID = os.environ["HESABPAY_ID"]

# Fixed AFN rate
USD_TO_AFN = 66

# Conversation states
LANG, AMOUNT, WALLET_TYPE, WALLET_INPUT, SCREENSHOT = range(5)

# Multi-language messages
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
            "💵 *Payment Instructions*\n"
            "----------------------------\n"
            "• *Total Amount:* {total:.2f} USD\n"
            "• *AFN Equivalent:* {total_afn:.2f} AFN (Rate: 66)\n"
            "----------------------------\n\n"
            "📤 *Please send the payment via HesabPay:*\n"
            "➡️ *HesabPay ID:* `{hesabpay}`\n\n"
            "🖼 After sending the money, upload your payment screenshot here."
        ),
        "ps": (
            "💵 *د تادیې لارښوونې*\n"
            "----------------------------\n"
            "• *ټول مبلغ:* {total:.2f} USD\n"
            "• *په افغانی کې:* {total_afn:.2f} AFN (نرخ: 66)\n"
            "----------------------------\n\n"
            "📤 *مهرباني وکړئ پیسې د HesabPay له لارې واستوئ:*\n"
            "➡️ *HesabPay ID:* `{hesabpay}`\n\n"
            "🖼 کله چې تادیه وکړئ، خپل سکرین شاټ دلته اپلوډ کړئ."
        ),
        "fa": (
            "💵 *راهنمای پرداخت*\n"
            "----------------------------\n"
            "• *مبلغ کل:* {total:.2f} USD\n"
            "• *معادل افغانی:* {total_afn:.2f} AFN (نرخ: 66)\n"
            "----------------------------\n\n"
            "📤 *لطفاً پرداخت را از طریق HesabPay ارسال کنید:*\n"
            "➡️ *ID HesabPay:* `{hesabpay}`\n\n"
            "🖼 پس از ارسال پول، اسکرین‌شات پرداخت را اینجا آپلود کنید."
        )
    },
    "ask_screenshot": {
        "en": "Please upload your payment screenshot:",
        "ps": "مهرباني وکړئ د تادیې سکرین شاټ اپلوډ کړئ:",
        "fa": "لطفاً اسکرین‌شات پرداخت خود را ارسال کنید:"
    },
    "order_sent": {
        "en": "Your order has been sent to admin. Waiting for approval.",
        "ps": "ستاسو فرمایش مدیر ته ولېږل شو. مهرباني وکړئ د تایید لپاره انتظار وکړئ.",
        "fa": "سفارش شما برای مدیر ارسال شد. لطفاً منتظر تایید باشید."
    },
    "approved_user": {
        "en": "✅ Your USDT has been delivered successfully!",
        "ps": "✅ ستاسو USDT په بریالیتوب سره واستول شو!",
        "fa": "✅ تتر شما با موفقیت ارسال شد!"
    },
    "rejected_user": {
        "en": "❌ Your order was rejected by admin.",
        "ps": "❌ ستاسو فرمایش د مدیر لخوا رد شو.",
        "fa": "❌ سفارش شما توسط مدیر رد شد."
    }
}

# Temporary local user storage
user_data_store = {}

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("English"), KeyboardButton("Pashto"), KeyboardButton("Dari")]]
    reply = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(MESSAGES["start"]["en"], reply_markup=reply)
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

    buttons = [
        ["10", "20", "30", "40", "50"],
        ["60", "70", "80", "90", "100"],
        ["Custom Amount"]
    ]
    reply = ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(MESSAGES["ask_amount"][lang], reply_markup=reply)
    return AMOUNT

# Enter amount
async def enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    lang = user_data_store[user_id]["lang"]
    txt = update.message.text

    if txt.lower() == "custom amount":
        await update.message.reply_text(
            "Enter custom USDT amount:" if lang == "en"
            else "خپل مقدار داخل کړئ:" if lang == "ps"
            else "مقدار مورد نظر را وارد کنید:"
        )
        return AMOUNT

    try:
        amount = float(txt)
    except:
        await update.message.reply_text(MESSAGES["ask_amount"][lang])
        return AMOUNT

    commission = 3 if 1 <= amount <= 100 else amount * 0.04
    total = round(amount + commission, 2)
    total_afn = round(total * USD_TO_AFN, 2)

    user_data_store[user_id].update({
        "amount": amount,
        "commission": commission,
        "total": total,
        "total_afn": total_afn
    })

    wallet_buttons = [["Binance ID", "TRC20 Wallet"]]
    reply = ReplyKeyboardMarkup(wallet_buttons, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(MESSAGES["ask_wallet_type"][lang], reply_markup=reply)
    return WALLET_TYPE

# Wallet type selection
async def choose_wallet_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    choice = update.message.text
    lang = user_data_store[user_id]["lang"]

    if "binance" in choice.lower():
        user_data_store[user_id]["wallet_type"] = "Binance ID"
    else:
        user_data_store[user_id]["wallet_type"] = "TRC20 Wallet"

    await update.message.reply_text(MESSAGES["ask_wallet_input"][lang])
    return WALLET_INPUT

# Wallet input
async def wallet_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    wallet = update.message.text.strip()
    lang = user_data_store[user_id]["lang"]

    user_data_store[user_id]["wallet"] = wallet

    total = user_data_store[user_id]["total"]
    total_afn = user_data_store[user_id]["total_afn"]

    msg = MESSAGES["payment_info"][lang].format(
        total=total,
        total_afn=total_afn,
        hesabpay=HESABPAY_ID
    )

    await update.message.reply_text(msg, parse_mode="Markdown")
    await update.message.reply_text(MESSAGES["ask_screenshot"][lang])
    return SCREENSHOT

# Screenshot
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
        f"📩 **New USDT Order**\n"
        f"👤 User: @{update.message.from_user.username}\n"
        f"🆔 Chat ID: {user_id}\n"
        f"💵 Amount: {order['amount']} USDT\n"
        f"💸 Commission: {order['commission']:.2f} USD\n"
        f"💰 Total: {order['total']:.2f} USD\n"
        f"🏦 Wallet Type: {order['wallet_type']}\n"
        f"🔐 Wallet: {order['wallet']}"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Done", callback_data=f"done_{user_id}")],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{user_id}")]
    ])

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=file_id,
        caption=caption,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

    await update.message.reply_text(MESSAGES["order_sent"][lang])
    return ConversationHandler.END

# Admin action
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, uid_str = query.data.split("_")
    user_id = int(uid_str)
    lang = user_data_store.get(user_id, {}).get("lang", "en")

    if action == "done":
        await context.bot.send_message(chat_id=user_id, text=MESSAGES["approved_user"][lang])
        await query.edit_message_caption(caption="✅ Order marked DONE by admin.")
    else:
        await context.bot.send_message(chat_id=user_id, text=MESSAGES["rejected_user"][lang])
        await query.edit_message_caption(caption="❌ Order REJECTED by admin.")

# Cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Order cancelled.")
    return ConversationHandler.END

# MAIN
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_language)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount)],
            WALLET_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_wallet_type)],
            WALLET_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_input)],
            SCREENSHOT: [MessageHandler(filters.PHOTO, screenshot)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(admin_action))

    print("Bot started...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
