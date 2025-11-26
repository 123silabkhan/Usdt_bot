# usdt_bot.py
"""
Final USDT marketplace bot (multi-lang EN/DR/PS)
- Seller registration (no ID), admin approval
- Sellers create orders (amount, rate, commission type/value, wallet account name & account id/address)
- Buyers see orders, choose seller, enter buy amount
- Commission computed (percent or fixed USD) per order amount (Option A)
- Buyer pays to HESABPAY_ID and uploads screenshot
- Admin receives screenshot + Approve/Reject buttons
- On admin approve -> seller notified to send USDT to buyer wallet
- Data persisted to JSON files: sellers.json, orders.json, requests.json
- No token hard-coded. Put BOT_TOKEN and HESABPAY_ID in environment.
"""

import os
import json
import math
from telegram import (
    Update, ReplyKeyboardMarkup, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters, ConversationHandler
)

# -----------------------
# CONFIG - change if needed
# -----------------------
ADMIN_ID = 6491173992  # admin telegram id (you confirmed)
BOT_TOKEN = os.getenv("BOT_TOKEN")  # must be set in Render env
HESABPAY_ID = os.getenv("HESABPAY_ID", "0729376719")  # set in env

# JSON files for persistence
SELLERS_FILE = "sellers.json"   # stores seller profiles (including 'approved' flag)
ORDERS_FILE = "orders.json"     # stores active sell orders per seller
REQUESTS_FILE = "requests.json" # stores pending buy requests (for admin processing)

# Ensure files exist
for f in (SELLERS_FILE, ORDERS_FILE, REQUESTS_FILE):
    if not os.path.exists(f):
        with open(f, "w") as fh:
            json.dump({}, fh)

# -----------------------
# UTIL: load/save json
# -----------------------
def load_json(path):
    with open(path, "r") as fh:
        try:
            return json.load(fh)
        except:
            return {}

def save_json(path, data):
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)

sellers = load_json(SELLERS_FILE)   # key: user_id (str) -> seller dict
orders = load_json(ORDERS_FILE)     # key: order_id (str) -> order dict
requests = load_json(REQUESTS_FILE) # key: req_id (str) -> buy request dict

# -----------------------
# Conversation states
# -----------------------
(
    LANG, HOME,

    # buyer flow
    BUY_SELECT_SELLER, BUY_ENTER_AMT, BUY_ENTER_BWALLET, BUY_UPLOAD_SLIP,

    # seller registration
    SELL_REG_NAME, SELL_REG_WA, SELL_REG_HESABPAY,

    # seller create order flow
    SELL_ORDER_AMT, SELL_ORDER_RATE,
    SELL_ORDER_COMTYPE, SELL_ORDER_COMVALUE,
    SELL_ORDER_WALLET_NAME, SELL_ORDER_WALLET_ID,

    # admin actions are via callback buttons
) = range(20)

# -----------------------
# Multi-language texts (EN / DR / PS)
# Keep key messages translated; you can expand any lines if desired.
# -----------------------
TXT = {
    "choose_language": {
        "en": "Choose language:",
        "fa": "زبان را انتخاب کنید:",
        "ps": "خپله ژبه وټاکئ:"
    },

    "main_menu": {
        "en": "🏠 Main Menu - Select an option",
        "fa": "🏠 منوی اصلی - یک گزینه را انتخاب کنید",
        "ps": "🏠 اصلي مېنو - یوه برخه وټاکئ"
    },

    "btn_buy": {"en": "💸 Buy USDT", "fa": "💸 خرید USDT", "ps": "💸 USDT اخیستل"},
    "btn_register": {"en": "🟦 Register as Seller", "fa": "🟦 ثبت فروشنده", "ps": "🟦 راجستر د خرڅوونکي په توګه"},
    "btn_create_order": {"en": "🛒 Create Sell Order", "fa": "🛒 ایجاد سفارش فروش", "ps": "🛒 د پلور امر جوړ کړئ"},
    "btn_sellers": {"en": "📜 Registered Sellers", "fa": "📜 فروشندگان ثبت‌شده", "ps": "📜 ثبت شوي پلورونکي"},
    "btn_lang": {"en": "🌐 Language", "fa": "🌐 زبان", "ps": "🌐 ژبه"},
    "btn_support": {"en": "📞 Support", "fa": "📞 پشتیبانی", "ps": "📞 ملاتړ"},

    # registration
    "ask_name": {"en":"Enter your full name:", "fa":"نام کامل خود را وارد کنید:", "ps":"خپل بشپړ نوم ولیکئ:"},
    "ask_wa": {"en":"Enter your WhatsApp number:", "fa":"شماره واتس‌اپ خود را وارد کنید:", "ps":"خپل واټس اپ نمبر ولیکئ:"},
    "ask_hesab": {"en":"Enter your HesabPay ID (for receiving payments):", "fa":"شناسه HesabPay خود را وارد کنید:", "ps":"خپل HesabPay ID ولیکئ:"},
    "reg_submitted": {"en":"✅ Registration submitted — admin will review.", "fa":"ثبت‌نام ارسال شد — مدیر بررسی می‌کند.", "ps":"رجسټرېشن واستول شو — مدیر به تایید کوي."},
    "not_approved": {"en":"❌ You are not an approved seller.", "fa":"❌ شما فروشنده تاییدشده نیستید.", "ps":"❌ تاسو منظور شوی پلورونکی نه یاست."},
    "approved_msg": {"en":"🎉 You were approved as seller! You can now create orders.", "fa":"تبریک! شما به عنوان فروشنده تایید شدید.", "ps":"🎉 تاسو د خرڅوونکي په توګه منظور شوئ! اوس تاسو امرونه جوړولی شئ."},

    # create order
    "ask_order_amount": {"en":"How many USDT will you sell (available limit)?", "fa":"چند USDT می‌خواهید برای فروش عرضه کنید؟", "ps":"تاسو څومره USDT د پلور لپاره لرئ؟"},
    "ask_order_rate": {"en":"Enter your selling rate (AFN per 1 USDT):", "fa":"نرخ فروش (افغانی برای هر USDT) را وارد کنید:", "ps":"ستاسو د پلور نرخ داخل کړئ (AFN هر USDT):"},
    "ask_commission_type": {"en":"Choose commission type for this order:", "fa":"نوع کمیسیون برای این سفارش را انتخاب کنید:", "ps":"د دې امر لپاره د کمېسیون ډول وټاکئ:"},
    "comm_types": {"en":["Percentage (%)","Fixed USD ($)"], "fa":["درصد (%)","مبلغ ثابت ($)"], "ps":["سلنه (%)","ثابته ډالر ($)"]},
    "ask_commission_value": {"en":"Enter commission value (just the number):", "fa":"مقدار کمیسیون را وارد کنید (فقط عدد):", "ps":"د کمیسیون مقدار ولیکئ (یوازې عدد):"},

    "ask_wallet_name": {"en":"Enter your account name (display name for wallet):", "fa":"نام حساب را وارد کنید:", "ps":"د حساب نوم داخل کړئ:"},
    "ask_wallet_id": {"en":"Enter your account ID/address (Binance ID, Bybit ID, or TRC20 address):", "fa":"شناسه/آدرس حساب را وارد کنید:", "ps":"د حساب ID/آدرس داخل کړئ:"},

    "order_saved": {"en":"✅ Sell order created and active.", "fa":"سفارش فروش ثبت شد و فعال است.", "ps":"✅ د پلور امر جوړ شو او فعال دی."},

    # buyer flow
    "select_seller": {"en":"Select a seller order to buy from:", "fa":"یک سفارش فروش را برای خرید انتخاب کنید:", "ps":"د پېرلو لپاره یو خرڅوونکي وټاکئ:"},
    "enter_buy_amount": {"en":"Enter how much USDT you want to buy:", "fa":"مقدار USDT برای خرید را وارد کنید:", "ps":"څومره USDT پېرل غواړئ؟ داخل کړئ:"},
    "invalid_amount": {"en":"Invalid amount. Try again.", "fa":"مقدار نامعتبر است. دوباره تلاش کنید.", "ps":"ناکاره مقدار. بیا هڅه وکړئ."},
    "payment_instructions": {
        "en": "Please send the AFN amount to our HesabPay:\nHesabPay ID: {hesab}\n\nAfter sending, upload payment screenshot here.",
        "fa": "لطفاً مبلغ را به HesabPay ما ارسال کنید:\nHesabPay ID: {hesab}\n\nپس از ارسال، اسکرین‌شات را آپلود کنید.",
        "ps": "مهرباني وکړئ پیسې زموږ HesabPay ته واستوئ:\nHesabPay ID: {hesab}\n\nوروسته د تادیې سکرین شاټ دلته اپلوډ کړئ."
    },

    "request_sent_admin": {"en":"✅ Payment screenshot sent to admin for confirmation.", "fa":"اسکرین‌شات پرداخت برای تایید به مدیر ارسال شد.", "ps":"د تادیې سکرین شاټ د تایید لپاره مدیر ته واستول شو."},

    # admin action texts
    "admin_new_request": {"en":"🆕 New buy request:", "fa":"🆕 درخواست خرید جدید:", "ps":"🆕 نوې د پېرلو غوښتنه:"},
    "admin_approve_msg": {"en":"Approve", "fa":"تایید", "ps":"منظور"},
    "admin_reject_msg": {"en":"Reject", "fa":"رد", "ps":"رد"},

    # confirmations
    "buyer_confirmed": {"en":"✅ Your purchase has been confirmed by admin. Wait while seller sends USDT.", "fa":"خرید شما توسط مدیر تایید شد. منتظر ارسال تتر از طرف فروشنده باشید.", "ps":"ستاسې پېرود د ادمین لخوا تایید شو. مهرباني وکړئ د پلورونکي لخوا د USDT لېږد ته انتظار وکړئ."}
}

# -----------------------
# HELPERS
# -----------------------
def lang_of(ctx):
    return ctx.user_data.get("lang", "en")

def saved_sellers_count():
    return len([s for s in sellers.values() if s.get("approved")])

def gen_id(prefix):
    import time, random
    return f"{prefix}_{int(time.time())}_{random.randint(1000,9999)}"

# -----------------------
# START & LANGUAGE
# -----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    context.user_data["lang"] = context.user_data.get("lang", "en")
    lang = context.user_data["lang"]

    kb = ReplyKeyboardMarkup([["English","Pashto","Dari"]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(TXT["choose_language"]["en"], reply_markup=kb)
    return LANG

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text
    if txt == "English":
        context.user_data["lang"] = "en"
    elif txt == "Dari":
        context.user_data["lang"] = "fa"
    elif txt == "Pashto":
        context.user_data["lang"] = "ps"
    else:
        context.user_data["lang"] = "en"

    lang = context.user_data["lang"]
    kb = ReplyKeyboardMarkup([
        [TXT["btn_buy"][lang]],
        [TXT["btn_register"][lang]],
        [TXT["btn_create_order"][lang]],
        [TXT["btn_sellers"][lang], TXT["btn_lang"][lang]]
    ], resize_keyboard=True)

    await update.message.reply_text(TXT["main_menu"][lang], reply_markup=kb)
    return HOME

# -----------------------
# HOME MENU HANDLER
# -----------------------
async def home_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "en")
    text = update.message.text

    # Buy flow
    if text == TXT["btn_buy"][lang]:
        return await buyer_list_orders(update, context)

    # Register as seller
    if text == TXT["btn_register"][lang]:
        await update.message.reply_text(TXT["ask_name"][lang], reply_markup=ReplyKeyboardRemove())
        return SELL_REG_NAME

    # Create sell order (only approved sellers)
    if text == TXT["btn_create_order"][lang]:
        uid = str(update.effective_user.id)
        if uid not in sellers or not sellers[uid].get("approved", False):
            await update.message.reply_text(TXT["not_approved"][lang], reply_markup=ReplyKeyboardRemove())
            return HOME
        # start order creation
        await update.message.reply_text(TXT["ask_order_amount"][lang], reply_markup=ReplyKeyboardRemove())
        return SELL_ORDER_AMT

    # Registered sellers list
    if text == TXT["btn_sellers"][lang]:
        return await show_registered_sellers(update, context)

    # change language
    if text == TXT["btn_lang"][lang]:
        kb = ReplyKeyboardMarkup([["English","Pashto","Dari"]], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(TXT["choose_language"]["en"], reply_markup=kb)
        return LANG

    if text == TXT["btn_support"][lang]:
        await update.message.reply_text(TXT["choose_language"]["en"])
        return HOME

    # default
    await update.message.reply_text(TXT["main_menu"][lang], reply_markup=ReplyKeyboardRemove())
    return HOME

# -----------------------
# SELLER REGISTRATION STEPS
# -----------------------
async def sell_reg_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg_name"] = update.message.text
    lang = context.user_data["lang"]
    await update.message.reply_text(TXT["ask_wa"][lang], reply_markup=ReplyKeyboardRemove())
    return SELL_REG_WA

async def sell_reg_wa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reg_wa"] = update.message.text
    lang = context.user_data["lang"]
    await update.message.reply_text(TXT["ask_hesab"][lang], reply_markup=ReplyKeyboardRemove())
    return SELL_REG_HESABPAY

async def sell_reg_hesab(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    lang = context.user_data["lang"]

    name = context.user_data.get("reg_name")
    wa = context.user_data.get("reg_wa")
    hesab = update.message.text

    # Save seller as pending (approved: False)
    sellers[user_id] = {
        "user_id": user_id,
        "name": name,
        "whatsapp": wa,
        "hesabpay": hesab,
        "approved": False,
        "lang": lang
    }
    save_json(SELLERS_FILE, sellers)

    # notify admin with approve/reject
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Approve", callback_data=f"approve_seller_{user_id}")],
        [InlineKeyboardButton("Reject", callback_data=f"reject_seller_{user_id}")]
    ])
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📩 New Seller Registration\n\nName: {name}\nWhatsApp: {wa}\nHesabPay: {hesab}\nUserID: {user_id}",
            reply_markup=kb
        )
    except Exception as e:
        print("Admin notification failed:", e)

    await update.message.reply_text(TXT["reg_submitted"][lang], reply_markup=main_menu_for(lang))
    return HOME

# -----------------------
# Helper: main menu keyboard for language
# -----------------------
def main_menu_for(lang):
    return ReplyKeyboardMarkup([
        [TXT["btn_buy"][lang]],
        [TXT["btn_register"][lang]],
        [TXT["btn_create_order"][lang]],
        [TXT["btn_sellers"][lang], TXT["btn_lang"][lang]]
    ], resize_keyboard=True)

# -----------------------
# ADMIN CALLBACKS (seller approve/reject)
# -----------------------
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("approve_seller_"):
        uid = data.split("_")[-1]
        if uid in sellers:
            sellers[uid]["approved"] = True
            save_json(SELLERS_FILE, sellers)
            # notify seller
            try:
                await context.bot.send_message(int(uid), TXT["approved_msg"][sellers[uid].get("lang","en")])
            except:
                pass
            await query.edit_message_text(f"Seller {sellers[uid]['name']} approved.")
        else:
            await query.edit_message_text("Seller not found.")

    elif data.startswith("reject_seller_"):
        uid = data.split("_")[-1]
        if uid in sellers:
            sellers[uid]["approved"] = False
            save_json(SELLERS_FILE, sellers)
            try:
                await context.bot.send_message(int(uid), TXT["seller_rejected"].get(sellers[uid].get("lang","en"), TXT["seller_rejected"]["en"]))
            except:
                pass
            await query.edit_message_text(f"Seller {uid} rejected.")
        else:
            await query.edit_message_text("Seller not found.")

    elif data.startswith("approve_buy_") or data.startswith("reject_buy_"):
        # admin approves or rejects a buy request (from requests DB)
        parts = data.split("_")
        action = parts[0]
        req_id = parts[-1]
        req = requests.get(req_id)
        if not req:
            await query.edit_message_text("Request not found.")
            return

        buyer_id = req["buyer_id"]
        seller_id = req["seller_id"]
        # on approve: notify buyer and notify seller
        if action == "approve":
            # notify buyer
            try:
                await context.bot.send_message(int(buyer_id), TXT["buyer_confirmed"]["en"])
            except:
                pass

            # notify seller with buyer wallet & ask to send USDT
            seller_msg = (
                f"📣 New Confirmed Order\n"
                f"Buyer ID: {buyer_id}\n"
                f"Amount: {req['amount']} USDT\n"
                f"Buyer Wallet: {req['buyer_wallet']}\n"
                f"Please send USDT to buyer and reply here when sent."
            )
            try:
                await context.bot.send_message(int(seller_id), seller_msg)
            except:
                pass

            await query.edit_message_text("Buy request approved. Seller notified.")
            # update seller's remaining amount
            if seller_id in orders:
                orders[seller_id]["amount"] = max(0, orders[seller_id]["amount"] - float(req["amount"]))
                save_json(ORDERS_FILE, orders)
            # remove request
            requests.pop(req_id, None)
            save_json(REQUESTS_FILE, requests)

        else:
            # reject
            try:
                await context.bot.send_message(int(buyer_id), "❌ Your payment was rejected by admin.")
            except:
                pass
            await query.edit_message_text("Buy request rejected.")
            requests.pop(req_id, None)
            save_json(REQUESTS_FILE, requests)

# -----------------------
# Seller create order steps
# -----------------------
async def seller_order_amt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ask amount
    txt = update.message.text
    # starting point: user clicked Create Sell Order, so we asked for amount earlier
    try:
        amt = float(txt)
    except:
        await update.message.reply_text(TXT["ask_order_amount"]["en"])  # fallback english
        return SELL_ORDER_AMT

    context.user_data["order_amount"] = amt
    await update.message.reply_text(TXT["ask_order_rate"][context.user_data.get("lang","en")], reply_markup=ReplyKeyboardRemove())
    return SELL_ORDER_RATE

async def seller_order_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        rate = float(update.message.text)
    except:
        await update.message.reply_text(TXT["ask_order_rate"][context.user_data.get("lang","en")])
        return SELL_ORDER_RATE

    context.user_data["order_rate"] = rate
    lang = context.user_data.get("lang","en")
    # commission type keyboard
    kb = ReplyKeyboardMarkup([[TXT["comm_types"][lang][0]], [TXT["comm_types"][lang][1]]], resize_keyboard=True)
    await update.message.reply_text(TXT["ask_commission_type"][lang], reply_markup=kb)
    return SELL_ORDER_COMTYPE

async def seller_order_comtype(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text
    lang = context.user_data.get("lang","en")
    # determine type
    if txt == TXT["comm_types"][lang][0]:
        context.user_data["order_comm_type"] = "percent"
    else:
        context.user_data["order_comm_type"] = "fixed"

    await update.message.reply_text(TXT["ask_commission_value"][lang], reply_markup=ReplyKeyboardRemove())
    return SELL_ORDER_COMVALUE

async def seller_order_comvalue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # number only
    try:
        val = float(update.message.text)
    except:
        await update.message.reply_text(TXT["ask_commission_value"][context.user_data.get("lang","en")])
        return SELL_ORDER_COMVALUE

    context.user_data["order_comm_value"] = val
    # now ask for wallet account name & id
    await update.message.reply_text(TXT["ask_wallet_name"][context.user_data.get("lang","en")])
    return SELL_ORDER_WALLET_NAME

async def seller_order_wallet_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["order_wallet_name"] = update.message.text
    await update.message.reply_text(TXT["ask_wallet_id"][context.user_data.get("lang","en")])
    return SELL_ORDER_WALLET_ID

async def seller_order_wallet_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet_id = update.message.text
    seller_id = str(update.message.from_user.id)
    # persist order
    order = {
        "seller_id": seller_id,
        "name": sellers[seller_id]["name"],
        "whatsapp": sellers[seller_id]["whatsapp"],
        "amount": float(context.user_data.get("order_amount")),
        "rate": float(context.user_data.get("order_rate")),
        "commission_type": context.user_data.get("order_comm_type"),
        "commission_value": float(context.user_data.get("order_comm_value")),
        "wallet_name": context.user_data.get("order_wallet_name"),
        "wallet_id": wallet_id
    }
    # store in orders under seller_id
    orders[seller_id] = order
    save_json(ORDERS_FILE, orders)
    await update.message.reply_text(TXT["order_saved"][context.user_data.get("lang","en")], reply_markup=main_menu_for(context.user_data.get("lang","en")))
    return HOME

# -----------------------
# Show registered sellers (simple)
# -----------------------
async def show_registered_sellers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang","en")
    lines = []
    for sid, s in sellers.items():
        if s.get("approved"):
            lines.append(f"{s['name']} — WhatsApp: {s['whatsapp']}")
    if not lines:
        await update.message.reply_text(TXT["no_sellers"][lang])
    else:
        await update.message.reply_text("\n".join(lines))
    return HOME

# -----------------------
# Buyer list orders (select seller order)
# -----------------------
async def buyer_list_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang","en")
    # gather active orders
    kb = []
    for sid, ord in orders.items():
        # only show if seller approved and amount > 0
        seller_profile = sellers.get(sid)
        if not seller_profile or not seller_profile.get("approved"):
            continue
        if float(ord.get("amount", 0)) <= 0:
            continue
        label = f"{ord['name']} — {ord['amount']} USDT — {ord['rate']} AFN"
        kb.append([label])
    if not kb:
        await update.message.reply_text(TXT["no_sellers"][lang], reply_markup=main_menu_for(lang))
        return HOME

    await update.message.reply_text(TXT["select_seller"][lang], reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return BUY_ENTER_AMT

# -----------------------
# Buyer selected order, ask buyer amount
# -----------------------
async def buyer_enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    # find matching order by seller name in label
    sel = None
    for sid, ord in orders.items():
        if ord["name"] in text:
            sel = ord
            break
    if not sel:
        await update.message.reply_text(TXT["no_sellers"][context.user_data.get("lang","en")], reply_markup=main_menu_for(context.user_data.get("lang","en")))
        return HOME

    context.user_data["selected_order"] = sel
    await update.message.reply_text(TXT["enter_buy_amount"][context.user_data.get("lang","en")], reply_markup=ReplyKeyboardRemove())
    return BUY_ENTER_BWALLET

# -----------------------
# Buyer enter amount & compute final amounts & instruct payment
# -----------------------
async def buyer_enter_wallet_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang","en")
    try:
        amount = float(update.message.text)
    except:
        await update.message.reply_text(TXT["invalid_amount"][lang])
        return BUY_ENTER_BWALLET

    sel = context.user_data.get("selected_order")
    if not sel:
        await update.message.reply_text("Order not found.", reply_markup=main_menu_for(lang))
        return HOME

    if amount > float(sel["amount"]):
        await update.message.reply_text("Seller doesn't have enough USDT available.", reply_markup=main_menu_for(lang))
        return HOME

    # compute commission
    comm_type = sel.get("commission_type")
    comm_val = float(sel.get("commission_value", 0))

    if comm_type == "percent":
        comm_usdt = (comm_val / 100.0) * amount
    else:
        # fixed USD per order (applies once)
        comm_usdt = float(comm_val)

    total_usdt = amount + comm_usdt
    rate_afn = float(sel.get("rate", 0))
    total_afn = total_usdt * rate_afn

    # save buy request to requests dict (pending screenshot)
    req_id = gen_id("req")
    buyer_id = str(update.message.from_user.id)
    requests[req_id] = {
        "req_id": req_id,
        "buyer_id": buyer_id,
        "seller_id": sel["seller_id"],
        "amount": amount,
        "commission_usdt": comm_usdt,
        "total_usdt": total_usdt,
        "total_afn": total_afn,
        "rate": rate_afn,
        "buyer_wallet": None,  # buyer will send wallet id next
        "status": "awaiting_wallet_and_payment"
    }
    save_json(REQUESTS_FILE, requests)

    # instruct buyer to send wallet id and payment to HesabPay
    instr = TXT["payment_instructions"][lang].format(hesab=HESABPAY_ID)
    # Show calculated totals too
    details = (
        f"Seller: {sel['name']}\n"
        f"Amount: {amount} USDT\n"
        f"Commission (USDT): {round(comm_usdt,6)}\n"
        f"Total to pay (USD equivalent): {round(total_usdt,6)}\n"
        f"Total AFN to send: {math.ceil(total_afn)} AFN\n\n"
        f"{instr}\n\n"
        f"Now reply with your receiving WALLET (TRC20 address) or account ID, then upload the payment screenshot."
    )

    await update.message.reply_text(details)
    # mark that this user is expected to send wallet id next (we track by buyer id and req_id)
    context.user_data["awaiting_req_id"] = req_id
    context.user_data["awaiting_wallet_for"] = req_id
    return BUY_UPLOAD_SLIP

# -----------------------
# Buyer provides wallet and then uploads screenshot
# -----------------------
async def buyer_upload_and_pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """We expect buyer to first send wallet/address as text, then send photo screenshot.
       We will handle both: if photo arrives and wallet known, forward to admin.
    """
    uid = str(update.message.from_user.id)
    lang = context.user_data.get("lang","en")
    # if text and awaiting wallet:
    if update.message.text and context.user_data.get("awaiting_wallet_for"):
        req_id = context.user_data["awaiting_wallet_for"]
        requests[req_id]["buyer_wallet"] = update.message.text
        save_json(REQUESTS_FILE, requests)
        await update.message.reply_text("Wallet saved. Now upload payment screenshot.", reply_markup=ReplyKeyboardRemove())
        return BUY_UPLOAD_SLIP

    # if photo: send to admin with approve/reject
    if update.message.photo and context.user_data.get("awaiting_wallet_for"):
        req_id = context.user_data["awaiting_wallet_for"]
        req = requests.get(req_id)
        if not req:
            await update.message.reply_text("Request not found.")
            return HOME

        # attach buyer wallet if not yet set
        buyer_wallet = req.get("buyer_wallet", "N/A")
        photo_file = update.message.photo[-1].file_id

        caption = (
            f"📩 {TXT['admin_new_request']['en']}\n\n"
            f"Request ID: {req_id}\n"
            f"Buyer ID: {req['buyer_id']}\n"
            f"Seller: {sellers[req['seller_id']]['name']}\n"
            f"Amount: {req['amount']} USDT\n"
            f"Commission (USDT): {req['commission_usdt']}\n"
            f"Total USD: {req['total_usdt']}\n"
            f"Total AFN: {math.ceil(req['total_afn'])}\n"
            f"Buyer Wallet: {buyer_wallet}\n"
        )
        # create admin approve/reject buttons - include req_id in callback
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Approve", callback_data=f"approve_buy_{req_id}")],
            [InlineKeyboardButton("Reject", callback_data=f"reject_buy_{req_id}")]
        ])
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_file, caption=caption, reply_markup=kb)
        await update.message.reply_text(TXT["request_sent_admin"][lang], reply_markup=main_menu_for(lang))
        # clear awaiting flags
        context.user_data.pop("awaiting_wallet_for", None)
        context.user_data.pop("awaiting_req_id", None)
        return HOME

    # otherwise prompt
    await update.message.reply_text("Please send your wallet address (text) first, then upload screenshot.")
    return BUY_UPLOAD_SLIP

# -----------------------
# Helper: main menu keyboard for language (copied)
# -----------------------
def main_menu_for(lang):
    return ReplyKeyboardMarkup([
        [TXT["btn_buy"][lang]],
        [TXT["btn_register"][lang]],
        [TXT["btn_create_order"][lang]],
        [TXT["btn_sellers"][lang], TXT["btn_lang"][lang]]
    ], resize_keyboard=True)

# -----------------------
# CANCEL handler
# -----------------------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang","en")
    await update.message.reply_text("Cancelled.", reply_markup=main_menu_for(lang))
    return HOME

# -----------------------
# Utility to generate IDs
# -----------------------
def gen_id(prefix):
    import time, random
    return f"{prefix}_{int(time.time())}_{random.randint(100,999)}"

# -----------------------
# MAIN: build app & handlers
# -----------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_language)],
            HOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, home_handler)],

            # seller registration
            SELL_REG_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_reg_name)],
            SELL_REG_WA: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_reg_wa)],
            SELL_REG_HESABPAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_reg_hesab)],

            # seller create order
            SELL_ORDER_AMT: [MessageHandler(filters.TEXT & ~filters.COMMAND, seller_order_amt)],
            SELL_ORDER_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, seller_order_rate)],
            SELL_ORDER_COMTYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, seller_order_comtype)],
            SELL_ORDER_COMVALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, seller_order_comvalue)],
            SELL_ORDER_WALLET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, seller_order_wallet_name)],
            SELL_ORDER_WALLET_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, seller_order_wallet_id)],

            # buyer flow
            BUY_ENTER_AMT: [MessageHandler(filters.TEXT & ~filters.COMMAND, buyer_enter_amount)],
            BUY_ENTER_BWALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, buyer_enter_wallet_amount)],
            BUY_UPLOAD_SLIP: [MessageHandler((filters.PHOTO | filters.TEXT) & ~filters.COMMAND, buyer_upload_and_pay)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(admin_callback))
    # also catch any text while in HOME (the ConversationHandler captures it); router not needed

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
