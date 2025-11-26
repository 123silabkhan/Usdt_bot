# ===============================================================
#  FULL PROFESSIONAL USDT TELEGRAM BOT
#  Seller System | Admin Approval | Orders | Commission
#  Multilanguage (English / Pashto / Dari)
#  Payment Screenshot Upload | Platform Commission
#  Render Deployment Ready
#  ADMIN ID = 6491173992
#  PAYMENT NAME = Mooj E-sarafi
#  PAYMENT ID = 0729376719
# ===============================================================

import os
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# ===============================================================
# CONFIG
# ===============================================================

ADMIN_ID = 6491173992
PAY_NAME = "Mooj E-sarafi"
PAY_ID = "0729376719"

# ===============================================================
# DATABASES (IN-MEMORY)
# ===============================================================

sessions = {}            # user_id → { lang, step, temp data }
sellers = {}             # seller_id → {name, phone, hesab, approved, wallet, commission_type, commission_value}
seller_orders = {}       # seller_id → list of orders
pending_payments = {}    # customer_id → {seller_id, amount }

# ===============================================================
# LANGUAGES
# ===============================================================

LANGUAGES = {
    "en": "🇺🇸 English",
    "ps": "🇦🇫 پښتو",
    "fa": "🇮🇷 دری"
}

# ===============================================================
# TRANSLATIONS
# ===============================================================

def t(lang, key):
    texts = {

        "welcome": {
            "en": "Welcome! Please choose your language:",
            "ps": "ښه راغلاست! مهرباني وکړئ خپله ژبه وټاکئ:",
            "fa": "خوش آمدید! لطفاً زبان خود را انتخاب کنید:"
        },

        "menu": {
            "en": "🏠 Main Menu",
            "ps": "🏠 اصلي مینو",
            "fa": "🏠 منوی اصلی"
        },

        "buy_usdt": {
            "en": "💵 Buy USDT",
            "ps": "💵 USDT اخیستل",
            "fa": "💵 خرید USDT"
        },

        "register_seller": {
            "en": "🟦 Register as Seller",
            "ps": "🟦 ځان د خرڅوونکي په توګه ثبت کړئ",
            "fa": "🟦 ثبت نام فروشنده"
        },

        "contact_admin": {
            "en": "📞 Contact Admin",
            "ps": "📞 د ادمین سره اړیکه",
            "fa": "📞 تماس با ادمین"
        },

        "enter_name": {
            "en": "Please send your full name:",
            "ps": "مهرباني وکړئ خپل بشپړ نوم ولیږئ:",
            "fa": "لطفاً نام کامل خود را ارسال کنید:"
        },

        "enter_phone": {
            "en": "Send your WhatsApp number:",
            "ps": "خپل واټساپ شمېره ولیږئ:",
            "fa": "شماره واتس‌اپ خود را ارسال کنید:"
        },

        "enter_hesab": {
            "en": "Send your HesabPay ID:",
            "ps": "خپل HesabPay آی ډي ولیږئ:",
            "fa": "شناسه HesabPay خود را وارد کنید:"
        },

        "seller_submitted": {
            "en": "Your seller registration is submitted. Wait for admin approval.",
            "ps": "ستاسو غوښتنلیک ولیږل شو. د اډمین تایید ته منتظر اوسئ.",
            "fa": "درخواست شما ارسال شد. منتظر تایید ادمین باشید."
        },

        "admin_new_seller": {
            "en": "📢 New Seller Registration:\n\nName: {}\nPhone: {}\nHesabPay ID: {}\n\nApprove?",
            "ps": "📢 د نوي خرڅوونکي غوښتنه:\n\nنوم: {}\nټیلفون: {}\nHesabPay ID: {}\n\nمنظور یې کړم؟",
            "fa": "📢 درخواست فروشنده جدید:\n\nنام: {}\nتلفن: {}\nHesabPay ID: {}\n\nتایید شود؟"
        },

        "seller_approved": {
            "en": "🎉 Your seller account is approved! You can now create orders.",
            "ps": "🎉 ستاسو د پلور حساب منظور شو! اوس امرونه جوړولی شئ.",
            "fa": "🎉 حساب فروشنده شما تایید شد! اکنون می‌توانید سفارش ثبت کنید."
        },

        "seller_panel": {
            "en": "Seller Panel:",
            "ps": "د خرڅوونکي پینل:",
            "fa": "پنل فروشنده:"
        },

        "create_order": {
            "en": "🟩 Create Order",
            "ps": "🟩 نوی امر جوړ کړئ",
            "fa": "🟩 ایجاد سفارش"
        },

        "enter_amount": {
            "en": "Enter USDT amount you want to sell:",
            "ps": "هغه مقدار USDT ولیکئ چې پلورل یې غواړئ:",
            "fa": "مقدار USDT مورد فروش را وارد کنید:"
        },

        "choose_commission": {
            "en": "Choose commission type:",
            "ps": "د کمیسیون ډول وټاکئ:",
            "fa": "نوع کمیسیون را انتخاب کنید:"
        },

        "percentage": {"en": "Percentage (%)", "ps": "سلنه (%)", "fa": "درصد (%)"},
        "fixed": {"en": "Fixed ($)", "ps": "ثابت ($)", "fa": "ثابت ($)"},

        "enter_commission": {
            "en": "Enter commission value:",
            "ps": "د کمیسیون مقدار ولیکئ:",
            "fa": "مقدار کمیسیون را وارد کنید:"
        },

        "enter_wallet": {
            "en": "Enter your TRC20 wallet address:",
            "ps": "خپل TRC20 والټ ولیکئ:",
            "fa": "آدرس کیف پول TRC20 خود را وارد کنید:"
        },

        "order_created": {
            "en": "✅ Your order has been created and is visible to customers.",
            "ps": "✅ ستاسو امر جوړ شو او مشتریان یې لیدلی شي.",
            "fa": "✅ سفارش شما ایجاد شد و برای مشتریان نمایش داده می‌شود."
        },

        "choose_seller": {
            "en": "Choose a seller:",
            "ps": "پلورونکی وټاکئ:",
            "fa": "فروشنده را انتخاب کنید:"
        },

        "enter_buy_amount": {
            "en": "Enter the amount of USDT you want to buy:",
            "ps": "هغه مقدار USDT ولیکئ چې اخیستل یې غواړئ:",
            "fa": "مقدار USDT مورد خرید را وارد کنید:"
        },

        "send_payment": {
            "en": f"Send the payment to following HesabPay account:\n\nName: {PAY_NAME}\nID: {PAY_ID}\n\nAfter payment, upload screenshot:",
            "ps": f"پیسې لاندې HesabPay حساب ته ولیږئ:\n\nنوم: {PAY_NAME}\nID: {PAY_ID}\n\nله تادیې وروسته سکرین‌شات پورته کړئ:",
            "fa": f"مبلغ را به حساب زیر واریز کنید:\n\nنام: {PAY_NAME}\nID: {PAY_ID}\n\nپس از پرداخت، اسکرین‌شات را ارسال کنید:"
        },

        "payment_received": {
            "en": "📸 Screenshot received. Admin will verify soon.",
            "ps": "📸 سکرین‌شات ترلاسه شو. اډمین به ژر تایید کړي.",
            "fa": "📸 اسکرین‌شات دریافت شد. ادمین به زودی تایید می‌کند."
        },

        "admin_verify": {
            "en": "Customer payment received.\n\nAmount: {}\nSeller ID: {}\n\nApprove?",
            "ps": "د مشتری تادیه ترلاسه شوه.\n\nمقدار: {}\nپلورونکی: {}\n\nمنظور کړم؟",
            "fa": "پرداخت مشتری دریافت شد.\n\nمقدار: {}\nفروشنده: {}\n\nتایید شود؟"
        },

        "notify_seller": {
            "en": "Send USDT to this wallet:\n{}",
            "ps": "USDT دې دې والټ ته واستوئ:\n{}",
            "fa": "USDT را به این کیف پول ارسال کنید:\n{}"
        },

        "platform_fee": {
            "en": "📌 Platform Commission:\n• $1 for 1–100 USDT\n• 1% for 100+ USDT",
            "ps": "📌 د پلاتفورم کمیسون:\n• $1 له 1–100 USDT پورې\n• 1% له 100+ USDT پورته",
            "fa": "📌 کمیسیون پلتفرم:\n• 1 دلار برای 1–100 USDT\n• 1٪ برای بیش از 100 USDT"
        }
    }

    return texts[key][lang]


# ===============================================================
# START COMMAND
# ===============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sessions[user_id] = {"lang": None, "step": None, "temp": {}}

    buttons = [
        [InlineKeyboardButton(LANGUAGES[k], callback_data=f"lang:{k}")]
        for k in LANGUAGES
    ]

    await update.message.reply_text(
        "Choose language:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ===============================================================
# LANGUAGE SELECTION
# ===============================================================

async def set_language(update, context):
    q = update.callback_query
    await q.answer()

    lang = q.data.split(":")[1]
    user = q.from_user.id

    sessions[user]["lang"] = lang

    buttons = [
        [InlineKeyboardButton(t(lang, "buy_usdt"), callback_data="buy")],
        [InlineKeyboardButton(t(lang, "register_seller"), callback_data="reg_s")],
        [InlineKeyboardButton(t(lang, "contact_admin"), callback_data="admin")]
    ]

    await q.edit_message_text(
        t(lang, "menu"),
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ===============================================================
# REGISTER SELLER (STEP 1)
# ===============================================================

async def cb_register_seller(update, context):
    q = update.callback_query
    await q.answer()
    user = q.from_user.id
    lang = sessions[user]["lang"]

    sessions[user]["step"] = "seller_name"

    await q.edit_message_text(
        t(lang, "enter_name"),
        reply_markup=ReplyKeyboardRemove()
    )


# ===============================================================
# SELLER TEXT INPUT HANDLER
# ===============================================================

async def seller_text(update, context):
    user = update.effective_user.id
    if user not in sessions or sessions[user]["step"] is None:
        return

    lang = sessions[user]["lang"]
    text = update.message.text
    step = sessions[user]["step"]

    # --------------------------------------
    # NAME
    # --------------------------------------
    if step == "seller_name":
        sessions[user]["temp"]["name"] = text
        sessions[user]["step"] = "seller_phone"

        await update.message.reply_text(
            t(lang, "enter_phone"),
            reply_markup=ReplyKeyboardRemove()
        )
        return

    # --------------------------------------
    # PHONE
    # --------------------------------------
    if step == "seller_phone":
        sessions[user]["temp"]["phone"] = text
        sessions[user]["step"] = "seller_hesab"

        await update.message.reply_text(t(lang, "enter_hesab"))
        return

    # --------------------------------------
    # HESAB
    # --------------------------------------
    if step == "seller_hesab":
        sessions[user]["temp"]["hesab"] = text
        data = sessions[user]["temp"]

        sellers[user] = {
            "name": data["name"],
            "phone": data["phone"],
            "hesab": data["hesab"],
            "approved": False,
            "wallet": None,
            "commission_type": None,
            "commission_value": None
        }

        sessions[user]["step"] = None

        await update.message.reply_text(t(lang, "seller_submitted"))

        # SEND TO ADMIN
        msg = t(lang, "admin_new_seller").format(
            data["name"], data["phone"], data["hesab"]
        )

        approve_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("Approve Seller", callback_data=f"approve_seller:{user}")]
        ])

        await context.bot.send_message(ADMIN_ID, msg, reply_markup=approve_btn)


# ===============================================================
# ADMIN APPROVES SELLER
# ===============================================================

async def approve_seller(update, context):
    q = update.callback_query
    await q.answer()
    seller_id = int(q.data.split(":")[1])

    sellers[seller_id]["approved"] = True

    lang = sessions[seller_id]["lang"]

    await context.bot.send_message(seller_id, t(lang, "seller_approved"))

    # seller panel
    await send_seller_panel(seller_id, context)


# ===============================================================
# SELLER PANEL
# ===============================================================

async def send_seller_panel(seller_id, context):
    lang = sessions[seller_id]["lang"]

    buttons = [
        [InlineKeyboardButton(t(lang, "create_order"), callback_data="create_order")]
    ]

    await context.bot.send_message(
        seller_id,
        t(lang, "seller_panel"),
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ===============================================================
# CREATE ORDER (SELLER)
# ===============================================================

async def cb_create_order(update, context):
    q = update.callback_query
    await q.answer()
    user = q.from_user.id
    lang = sessions[user]["lang"]

    sessions[user]["step"] = "order_amount"

    await q.edit_message_text(t(lang, "enter_amount"))


async def seller_order_input(update, context):
    user = update.effective_user.id
    if user not in sessions or sessions[user]["step"] is None:
        return

    lang = sessions[user]["lang"]
    text = update.message.text
    step = sessions[user]["step"]

    temp = sessions[user]["temp"]

    # -------------------------------------
    # AMOUNT
    # -------------------------------------
    if step == "order_amount":
        temp["amount"] = float(text)
        sessions[user]["step"] = "commission_type"

        buttons = [
            [
                InlineKeyboardButton(t(lang, "percentage"), callback_data="c_type:percent"),
                InlineKeyboardButton(t(lang, "fixed"), callback_data="c_type:fixed"),
            ]
        ]

        await update.message.reply_text(
            t(lang, "choose_commission"),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # -------------------------------------
    # COMMISSION VALUE
    # -------------------------------------
    if step == "commission_value":
        temp["commission_value"] = float(text)
        sessions[user]["step"] = "wallet_address"

        await update.message.reply_text(t(lang, "enter_wallet"))
        return

    # -------------------------------------
    # WALLET ADDRESS
    # -------------------------------------
    if step == "wallet_address":
        temp["wallet"] = text

        sellers[user]["wallet"] = temp["wallet"]
        sellers[user]["commission_type"] = temp["commission_type"]
        sellers[user]["commission_value"] = temp["commission_value"]

        # Save order
        seller_orders.setdefault(user, [])
        seller_orders[user].append({
            "amount": temp["amount"],
            "commission_type": temp["commission_type"],
            "commission_value": temp["commission_value"],
            "wallet": temp["wallet"]
        })

        sessions[user]["step"] = None
        sessions[user]["temp"] = {}

        await update.message.reply_text(t(lang, "order_created"))

        await send_seller_panel(user, context)


# ===============================================================
# COMMISSION CALLBACK
# ===============================================================

async def cb_commission_type(update, context):
    q = update.callback_query
    await q.answer()
    user = q.from_user.id

    lang = sessions[user]["lang"]
    c_type = q.data.split(":")[1]

    sessions[user]["temp"]["commission_type"] = c_type
    sessions[user]["step"] = "commission_value"

    await q.edit_message_text(t(lang, "enter_commission"))


# ===============================================================
# BUY USDT
# ===============================================================

async def cb_buy(update, context):
    q = update.callback_query
    await q.answer()
    user = q.from_user.id
    lang = sessions[user]["lang"]

    # list all sellers with approved status
    buttons = []
    for sid, data in sellers.items():
        if data["approved"]:
            for order in seller_orders.get(sid, []):
                buttons.append([InlineKeyboardButton(
                    f"{data['name']} — {order['amount']} USDT",
                    callback_data=f"choose_seller:{sid}"
                )])

    if not buttons:
        await q.edit_message_text("No sellers available now.")
        return

    await q.edit_message_text(
        t(lang, "choose_seller"),
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ===============================================================
# SELECT SELLER → ENTER BUY AMOUNT
# ===============================================================

async def cb_choose_seller(update, context):
    q = update.callback_query
    await q.answer()

    user = q.from_user.id
    seller_id = int(q.data.split(":")[1])

    lang = sessions[user]["lang"]

    sessions[user]["temp"]["seller_id"] = seller_id
    sessions[user]["step"] = "buy_amount"

    await q.edit_message_text(t(lang, "enter_buy_amount"))


async def buy_amount(update, context):
    user = update.effective_user.id
    if sessions[user]["step"] != "buy_amount":
        return

    lang = sessions[user]["lang"]

    amount = float(update.message.text)
    seller_id = sessions[user]["temp"]["seller_id"]

    # Save pending payment
    pending_payments[user] = {
        "amount": amount,
        "seller_id": seller_id
    }

    sessions[user]["step"] = "payment_screenshot"

    fee_text = t(lang, "platform_fee")

    await update.message.reply_text(fee_text)
    await update.message.reply_text(t(lang, "send_payment"))


# ===============================================================
# PAYMENT SCREENSHOT
# ===============================================================

async def receive_screenshot(update, context):
    user = update.effective_user.id

    if user not in pending_payments:
        return

    lang = sessions[user]["lang"]

    await update.message.reply_text(t(lang, "payment_received"))

    data = pending_payments[user]

    # Send to admin
    seller_id = data["seller_id"]
    amount = data["amount"]

    msg = t(lang, "admin_verify").format(amount, seller_id)

    approve_btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("Approve Payment", callback_data=f"pay_ok:{user}")]
    ])

    photo = update.message.photo[-1].file_id
    await context.bot.send_photo(
        ADMIN_ID,
        photo,
        caption=msg,
        reply_markup=approve_btn
    )


# ===============================================================
# ADMIN APPROVES PAYMENT
# ===============================================================

async def cb_pay_ok(update, context):
    q = update.callback_query
    await q.answer()

    customer_id = int(q.data.split(":")[1])
    data = pending_payments[customer_id]
    seller_id = data["seller_id"]
    amount = data["amount"]

    seller_wallet = sellers[seller_id]["wallet"]
    lang = sessions[seller_id]["lang"]

    msg = t(lang, "notify_seller").format(seller_wallet)

    await context.bot.send_message(seller_id, msg)

    # delete pending
    del pending_payments[customer_id]


# ===============================================================
# COMMAND: /start resets everything
# ===============================================================

async def cmd_start(update, context):
    await start(update, context)


# ===============================================================
# BUILD APPLICATION
# ===============================================================

def main():
    app = ApplicationBuilder().token("YOUR_TELEGRAM_BOT_TOKEN_HERE").build()

    # commands
    app.add_handler(CommandHandler("start", cmd_start))

    # callbacks
    app.add_handler(CallbackQueryHandler(set_language, pattern="^lang"))
    app.add_handler(CallbackQueryHandler(cb_register_seller, pattern="^reg_s"))
    app.add_handler(CallbackQueryHandler(cb_buy, pattern="^buy"))
    app.add_handler(CallbackQueryHandler(cb_create_order, pattern="^create_order"))
    app.add_handler(CallbackQueryHandler(cb_commission_type, pattern="^c_type"))
    app.add_handler(CallbackQueryHandler(cb_choose_seller, pattern="^choose_seller"))
    app.add_handler(CallbackQueryHandler(approve_seller, pattern="^approve_seller"))
    app.add_handler(CallbackQueryHandler(cb_pay_ok, pattern="^pay_ok"))

    # text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, seller_text))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, seller_order_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, buy_amount))

    # screenshot
    app.add_handler(MessageHandler(filters.PHOTO, receive_screenshot))

    print("BOT IS RUNNING...")
    app.run_polling()


if __name__ == "__main__":
    main()
