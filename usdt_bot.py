# usdt_bot.py
# --------------------------------------
# Multilingual USDT Marketplace Bot
# English • Dari • Pashto
# --------------------------------------

import os
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
    ConversationHandler
)

# -------------------------
# CONFIG
# -------------------------
ADMINS = ["6491173992"]  # <-- YOUR ADMIN ID

# You will add TOKEN manually in Render
TOKEN = os.getenv("BOT_TOKEN")

# -------------------------
# LANGUAGES
# -------------------------

LANGUAGES = {
    "en": "🇺🇸 English",
    "fa": "🇦🇫 Dari",
    "ps": "🇦🇫 Pashto"
}

# -------------------------
# TEXTS (Multilingual)
# -------------------------
TEXT = {
    "start": {
        "en": "Welcome to the USDT Marketplace Bot! Please choose an option:",
        "fa": "به ربات خرید و فروش USDT خوش آمدید! لطفاً یکی از گزینه‌ها را انتخاب کنید:",
        "ps": "د USDT بازار موند روباټ ته ښه راغلاست! مهرباني وکړئ یوه تڼۍ وټاکئ:"
    },

    "main_menu": {
        "en": ["💸 Buy USDT", "🟦 Register as Seller", "📜 Registered Sellers", "🌐 Language", "📞 Support"],
        "fa": ["💸 خرید USDT", "🟦 ثبت‌نام حیث فروشنده", "📜 فروشندگان ثبت‌شده", "🌐 زبان", "📞 پشتیبانی"],
        "ps": ["💸 USDT اخیستل", "🟦 د پلورونکي په توګه ثبت کول", "📜 ثبت شوي پلورونکي", "🌐 ژبه", "📞 ملاتړ"]
    },

    "choose_language": {
        "en": "Choose your language:",
        "fa": "زبان خود را انتخاب کنید:",
        "ps": "خپله ژبه وټاکئ:"
    },

    "seller_intro": {
        "en": "To register as a seller, please enter your full name:",
        "fa": "برای ثبت‌نام به حیث فروشنده، لطفاً نام کامل خود را وارد کنید:",
        "ps": "د پلورونکي په توګه د ثبت لپاره، مهرباني وکړئ خپل بشپړ نوم ولیکئ:"
    },

    "ask_whatsapp": {
        "en": "Enter your WhatsApp number:",
        "fa": "شماره واتس‌اپ خود را وارد کنید:",
        "ps": "خپل واټس اپ شمیره دننه کړئ:"
    },

    "ask_hesabpay": {
        "en": "Enter your HesabPay ID:",
        "fa": "شناسه HesabPay خود را وارد کنید:",
        "ps": "خپل HesabPay پېژند نمبر ولیکئ:"
    },

    "ask_method": {
        "en": "Choose USDT delivery method:",
        "fa": "روش ارسال USDT را انتخاب کنید:",
        "ps": "د USDT لېږلو طریقه وټاکئ:"
    },

    "methods": {
        "en": ["Binance ID", "Bybit ID", "TRC20 Wallet", "All Methods"],
        "fa": ["شناسه Binance", "شناسه Bybit", "والت TRC20", "همه روش‌ها"],
        "ps": ["د Binance پېژند", "د Bybit پېژند", "TRC20 والټ", "ټولې طریقې"]
    },

    "ask_amount": {
        "en": "Enter the amount of USDT you want to sell:",
        "fa": "مقدار USDT را که می‌خواهید بفروشید وارد کنید:",
        "ps": "دا USDT اندازه ولیکئ چې پلورل غواړئ:"
    },

    "ask_rate": {
        "en": "Enter your selling rate (per USDT):",
        "fa": "نرخ فروش خود را وارد کنید (برای هر USDT):",
        "ps": "د پلور نرخ ولیکئ (پر USDT):"
    },

    "seller_submitted": {
        "en": "Your seller registration has been submitted. Admin will review it.",
        "fa": "درخواست شما برای ثبت‌نام فروشنده ارسال شد. مدیر آن را بررسی می‌کند.",
        "ps": "ستاسې د پلورونکي غوښتنلیک واستول شو. ادمین به یې تایید کړي."
    },

    "seller_approved": {
        "en": "Your seller account has been approved!",
        "fa": "اکانت فروشنده شما تایید شد!",
        "ps": "ستاسې د پلور اکانټ منظور شو!"
    },

    "registered_sellers_title": {
        "en": "📜 Registered Sellers:",
        "fa": "📜 فروشندگان ثبت‌شده:",
        "ps": "📜 ثبت شوي پلورونکي:"
    },

    "no_sellers": {
        "en": "No sellers available yet.",
        "fa": "هنوز هیچ فروشنده‌ای موجود نیست.",
        "ps": "تر اوسه هیڅ پلورونکي نشته."
    },

    "support": {
        "en": "📞 Support: Contact admin on WhatsApp.",
        "fa": "📞 پشتیبانی: از طریق واتس‌اپ با مدیر تماس بگیرید.",
        "ps": "📞 ملاتړ: له ادمین سره په واټس‌اپ اړیکه ونیسئ."
    }
}

# -------------------------
# STORAGE
# -------------------------
users_lang = {}
pending_sellers = {}
approved_sellers = {}

# -------------------------
# STATES
# -------------------------
(
    REGISTER_NAME,
    REGISTER_WHATSAPP,
    REGISTER_HESABPAY,
    REGISTER_METHOD,
    REGISTER_AMOUNT,
    REGISTER_RATE
) = range(6)

# -------------------------
# HANDLERS
# -------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)

    if uid not in users_lang:
        users_lang[uid] = "en"

    lang = users_lang[uid]

    main_kb = ReplyKeyboardMarkup(
        [[btn] for btn in TEXT["main_menu"][lang]],
        resize_keyboard=True
    )

    await update.message.reply_text(TEXT["start"][lang], reply_markup=main_kb)


# ---------- LANGUAGE ----------

async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    lang = users_lang.get(uid, "en")

    kb = ReplyKeyboardMarkup(
        [[LANGUAGES[l]] for l in LANGUAGES],
        resize_keyboard=True
    )

    await update.message.reply_text(TEXT["choose_language"][lang], reply_markup=kb)


async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    choice = update.message.text

    for code, label in LANGUAGES.items():
        if choice == label:
            users_lang[uid] = code
            return await start(update, context)

    await update.message.reply_text("Invalid language.")


# ---------- REGISTER AS SELLER ----------

async def register_seller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    lang = users_lang[uid]

    pending_sellers[uid] = {}

    await update.message.reply_text(TEXT["seller_intro"][lang])
    return REGISTER_NAME


async def reg_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    lang = users_lang[uid]

    pending_sellers[uid]["name"] = update.message.text

    await update.message.reply_text(TEXT["ask_whatsapp"][lang])
    return REGISTER_WHATSAPP


async def reg_whatsapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    lang = users_lang[uid]

    pending_sellers[uid]["whatsapp"] = update.message.text

    kb = ReplyKeyboardMarkup(
        [[m] for m in TEXT["methods"][lang]],
        resize_keyboard=True
    )

    await update.message.reply_text(TEXT["ask_method"][lang], reply_markup=kb)
    return REGISTER_METHOD


async def reg_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    lang = users_lang[uid]

    pending_sellers[uid]["method"] = update.message.text

    await update.message.reply_text(TEXT["ask_hesabpay"][lang])
    return REGISTER_HESABPAY


async def reg_hesabpay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    lang = users_lang[uid]

    pending_sellers[uid]["hesabpay"] = update.message.text

    await update.message.reply_text(TEXT["ask_amount"][lang])
    return REGISTER_AMOUNT


async def reg_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    lang = users_lang[uid]

    pending_sellers[uid]["amount"] = update.message.text

    await update.message.reply_text(TEXT["ask_rate"][lang])
    return REGISTER_RATE


async def reg_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    lang = users_lang[uid]

    pending_sellers[uid]["rate"] = update.message.text

    # Notify admin
    text = f"🆕 NEW SELLER REGISTRATION:\n\n" \
           f"Name: {pending_sellers[uid]['name']}\n" \
           f"WhatsApp: {pending_sellers[uid]['whatsapp']}\n" \
           f"HesabPay: {pending_sellers[uid]['hesabpay']}\n" \
           f"Method: {pending_sellers[uid]['method']}\n" \
           f"Amount: {pending_sellers[uid]['amount']}\n" \
           f"Rate: {pending_sellers[uid]['rate']}\n\n" \
           f"Approve seller?"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Approve", callback_data=f"approve_{uid}")]
    ])

    for admin in ADMINS:
        try:
            await context.bot.send_message(admin, text, reply_markup=kb)
        except:
            pass

    await update.message.reply_text(TEXT["seller_submitted"][lang])
    return ConversationHandler.END


async def approve_seller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    uid = query.data.replace("approve_", "")

    approved_sellers[uid] = pending_sellers[uid]

    await query.edit_message_text("Seller approved.")

    # Notify seller
    try:
        lang = users_lang.get(uid, "en")
        await context.bot.send_message(uid, TEXT["seller_approved"][lang])
    except:
        pass


# ---------- SHOW REGISTERED SELLERS ----------

async def show_sellers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    lang = users_lang.get(uid, "en")

    if not approved_sellers:
        await update.message.reply_text(TEXT["no_sellers"][lang])
        return

    msg = TEXT["registered_sellers_title"][lang] + "\n\n"

    for sid, s in approved_sellers.items():
        msg += (
            f"👤 {s['name']}\n"
            f"📱 WhatsApp: {s['whatsapp']}\n"
            f"💳 HesabPay: {s['hesabpay']}\n"
            f"📦 Method: {s['method']}\n"
            f"💰 Amount: {s['amount']} USDT\n"
            f"🏷 Rate: {s['rate']}\n"
            f"----------------------\n"
        )

    await update.message.reply_text(msg)


# ---------- SUPPORT ----------

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    lang = users_lang[uid]

    await update.message.reply_text(TEXT["support"][lang])


# -------------------------
# MAIN FUNCTION
# -------------------------

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    reg_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("Register as Seller|ثبت‌نام حیث فروشنده|د پلورونکي په توګه ثبت کول"),
                           register_seller)
        ],
        states={
            REGISTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_name)],
            REGISTER_WHATSAPP: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_whatsapp)],
            REGISTER_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_method)],
            REGISTER_HESABPAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_hesabpay)],
            REGISTER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_amount)],
            REGISTER_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_rate)],
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))

    app.add_handler(reg_conv)
    app.add_handler(CallbackQueryHandler(approve_seller, pattern="approve_"))

    app.add_handler(MessageHandler(filters.Regex("Language|زبان|ژبه"), language))
    app.add_handler(MessageHandler(filters.Regex("English|Dari|Pashto"), set_language))

    app.add_handler(MessageHandler(filters.Regex("Registered Sellers|فروشندگان ثبت‌شده|ثبت شوي پلورونکي"), show_sellers))
    app.add_handler(MessageHandler(filters.Regex("Support|پشتیبانی|ملاتړ"), support))

    app.run_polling()


if __name__ == "__main__":
    main()
