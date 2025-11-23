import os
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
    ConversationHandler
)

# Load environment variables (Render)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 6491173992))
HESABPAY_ID = os.getenv("HESABPAY_ID", "0729376719")

# Fixed AFN rate
USD_TO_AFN = 66

# STATES
LANG, AMOUNT, WALLET_TYPE, WALLET, SCREENSHOT = range(5)

# Messages
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

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("English"), KeyboardButton("Pashto"), KeyboardButton("Dari")]
    ]
    markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    await update.message.reply_text(MESSAGES["start"]["en"], reply_markup=markup)
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

    context.user_data["lang"] = lang
    await update.message.reply_text(MESSAGES["ask_amount"][lang])
    return AMOUNT


# Amount input
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

    # Wallet type buttons
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🟡 Binance ID", callback_data="wallet_binance")],
        [InlineKeyboardButton("🔵 TRC20 Wallet", callback_data="wallet_trc20")]
    ])

    await update.message.reply_text("Choose your wallet type:", reply_markup=keyboard)
    return WALLET_TYPE


# Wallet type selection
async def select_wallet_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "wallet_binance":
        context.user_data["wallet_type"] = "Binance ID"
        await query.edit_message_text("Please enter your Binance ID:")
    else:
        context.user_data["wallet_type"] = "TRC20 Wallet"
        await query.edit_message_text("Please enter your TRC20 wallet address:")

    return WALLET


# Wallet input
async def enter_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet = update.message.text
    context.user_data["wallet"] = wallet
    lang = context.user_data["lang"]

    total_usd = context.user_data["total"]
    total_afn = total_usd * USD_TO_AFN

    # 🌟 Improved Payment Message
    msg = (
        "💵 *Payment Instructions*\n"
        "----------------------------\n"
        f"• *Total Amount:* {total_usd:.2f} USD\n"
        f"• *AFN Equivalent:* {total_afn:.2f} AFN\n"
        f"• *Rate:* {USD_TO_AFN} AFN per USD\n"
        "----------------------------\n\n"
        "📤 *Please send the payment via HesabPay:*\n"
        f"➡️ *HesabPay ID:* `{HESABPAY_ID}`\n\n"
        "🖼 After sending the money, upload your payment screenshot here."
    )

    await update.message.reply_text(msg, parse_mode="Markdown")
    return SCREENSHOT


# Screenshot handler
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


# Admin done/cancel
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
