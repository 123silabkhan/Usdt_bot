import os
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters, ConversationHandler
)

# Render environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 6491173992))
HESABPAY_ID = os.getenv("HESABPAY_ID", "0729376719")

# Fixed AFN exchange rate
USD_TO_AFN = 66

# Conversation states
LANG, AMOUNT, WALLET_TYPE, WALLET, SCREENSHOT = range(5)

# Multi-language messages
MESSAGES = {
    "start": {
        "en": "Welcome! Please select your language:",
        "ps": "ښه راغلاست! مهرباني وکړئ خپله ژبه وټاکئ:",
        "fa": "خوش آمدید! لطفاً زبان خود را انتخاب کنید:"
    },

    "ask_amount": {
        "en": "Enter the amount of USDT you want to buy:",
        "ps": "مهرباني وکړئ د هغه مقدار USDT داخل کړئ چې غواړئ یې واخلئ:",
        "fa": "لطفاً مقدار USDT که می‌خواهید خریداری کنید وارد کنید:"
    },

    "choose_wallet_type": {
        "en": "Choose your wallet type:",
        "ps": "مهرباني وکړئ د خپل والټ ډول انتخاب کړئ:",
        "fa": "لطفاً نوع کیف پول خود را انتخاب کنید:"
    },

    "enter_binance": {
        "en": "Please enter your Binance ID:",
        "ps": "مهرباني وکړئ خپل د بایننس آی ډي داخل کړئ:",
        "fa": "لطفاً شناسه Binance خود را وارد کنید:"
    },

    "enter_trc20": {
        "en": "Please enter your TRC20 wallet address:",
        "ps": "مهرباني وکړئ د خپل TRC20 والټ آدرس داخل کړئ:",
        "fa": "لطفاً آدرس کیف پول TRC20 خود را وارد کنید:"
    },

    "ask_screenshot": {
        "en": "Please upload your payment screenshot:",
        "ps": "مهرباني وکړئ د تادیې سکرین شاټ اپلوډ کړئ:",
        "fa": "لطفاً اسکرین‌شات پرداخت خود را ارسال کنید:"
    },

    "order_sent": {
        "en": "Your order has been sent to admin. Waiting for approval.",
        "ps": "ستاسو فرمایش مدیر ته ولېږل شو. مهرباني وکړئ د تایید تر وخته پورې انتظار وکړئ.",
        "fa": "سفارش شما به مدیر ارسال شد. لطفاً تا زمان تأیید منتظر بمانید."
    },

    "payment_title": {
        "en": "💵 *Payment Instructions*",
        "ps": "💵 *د تادیې لارښوونې*",
        "fa": "💵 *راهنمای پرداخت*"
    },

    "send_hesabpay": {
        "en": "📤 *Please send the payment via HesabPay:*",
        "ps": "📤 *مهرباني وکړئ پیسې د HesabPay له لارې واستوئ:*",
        "fa": "📤 *لطفاً پرداخت را از طریق HesabPay ارسال کنید:*"
    },

    "after_payment": {
        "en": "🖼 After sending the money, upload your payment screenshot here.",
        "ps": "🖼 کله چې تادیه ترسره کړئ، مهرباني وکړئ خپل د تادیې سکرین شاټ دلته اپلوډ کړئ.",
        "fa": "🖼 پس از ارسال پول، لطفاً اسکرین‌شات پرداخت را اینجا ارسال کنید."
    }
}


# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("English"), KeyboardButton("Pashto"), KeyboardButton("Dari")]
    ]

    markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    await update.message.reply_text(MESSAGES["start"]["en"], reply_markup=markup)
    return LANG


# Language Selection
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

    context.user_data["lang"] = lang
    await update.message.reply_text(MESSAGES["ask_amount"][lang])
    return AMOUNT


# Amount Entering
async def enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data["lang"]

    try:
        amount = float(update.message.text)
    except:
        await update.message.reply_text(MESSAGES["ask_amount"][lang])
        return AMOUNT

    commission = 3 if 1 <= amount <= 100 else amount * 0.04
    total = amount + commission

    context.user_data.update({
        "amount": amount,
        "commission": commission,
        "total": total
    })

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🟡 Binance ID", callback_data="wallet_binance")],
        [InlineKeyboardButton("🔵 TRC20 Wallet", callback_data="wallet_trc20")]
    ])

    await update.message.reply_text(MESSAGES["choose_wallet_type"][lang], reply_markup=keyboard)
    return WALLET_TYPE


# Wallet Type Choose
async def select_wallet_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = context.user_data["lang"]

    if query.data == "wallet_binance":
        context.user_data["wallet_type"] = "Binance ID"
        await query.edit_message_text(MESSAGES["enter_binance"][lang])
    else:
        context.user_data["wallet_type"] = "TRC20 Wallet"
        await query.edit_message_text(MESSAGES["enter_trc20"][lang])

    return WALLET


# Wallet Entering
async def enter_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet = update.message.text
    context.user_data["wallet"] = wallet
    lang = context.user_data["lang"]

    total_usd = context.user_data["total"]
    total_afn = total_usd * USD_TO_AFN

    msg = (
        f"{MESSAGES['payment_title'][lang]}\n"
        "----------------------------\n"
        f"• *Total Amount:* {total_usd:.2f} USD\n"
        f"• *AFN Equivalent:* {total_afn:.2f} AFN\n"
        f"• *Rate:* {USD_TO_AFN} AFN per USD\n"
        "----------------------------\n\n"
        f"{MESSAGES['send_hesabpay'][lang]}\n"
        f"➡️ *HesabPay ID:* `{HESABPAY_ID}`\n\n"
        f"{MESSAGES['after_payment'][lang]}"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")
    return SCREENSHOT


# Screenshot Handler
async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data["lang"]

    if not update.message.photo:
        await update.message.reply_text(MESSAGES["ask_screenshot"][lang])
        return SCREENSHOT

    file_id = update.message.photo[-1].file_id
    context.user_data["screenshot"] = file_id

    order = context.user_data
    user_id = update.message.from_user.id

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


# Admin Actions
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, user_id = query.data.split("_")
    user_id = int(user_id)

    if action == "done":
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ Your USDT has been delivered. Thank you!"
        )
        await query.edit_message_caption(
            caption="✅ Order marked as DONE by admin.",
            parse_mode="Markdown"
        )

    elif action == "cancel":
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Your order was rejected by admin."
        )
        await query.edit_message_caption(
            caption="❌ Order REJECTED by admin.",
            parse_mode="Markdown"
        )


# Cancel Command
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Order cancelled.")
    return ConversationHandler.END


# Main Function
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_language)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount)],
            WALLET_TYPE: [CallbackQueryHandler(select_wallet_type)],
            WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_wallet)],
            SCREENSHOT: [MessageHandler(filters.PHOTO | filters.TEXT, screenshot)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(admin_action))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
