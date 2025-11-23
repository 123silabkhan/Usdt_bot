# usdt_bot.py
import os
import asyncio
import logging
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, Any

from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters, ConversationHandler
)

# ---------------- Configuration ----------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6491173992"))  # single admin
HESABPAY_ID = os.getenv("HESABPAY_ID", "0729376719")

# default AFN rate (can be changed via /rate)
AFN_RATE = float(os.getenv("AFN_RATE", "66"))

# Live rate fetch interval (minutes). Set to 0 to disable automatic fetch.
LIVE_RATE_INTERVAL_MIN = int(os.getenv("LIVE_RATE_INTERVAL_MIN", "30"))

# Daily report time (UTC) as HH:MM
DAILY_REPORT_TIME_UTC = os.getenv("DAILY_REPORT_TIME_UTC", "00:00")

# Anti-flood: minimum seconds between sensitive actions per user
MIN_ACTION_SECONDS = 2

# Commission policy
def compute_commission(amount: float) -> float:
    return 3.0 if 1 <= amount <= 100 else amount * 0.04

# ---------------- Logging ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("usdt_bot")

# ---------------- In-memory stores ----------------
_next_order_id = 1
orders: Dict[int, Dict[str, Any]] = {}         # order_id -> order dict
user_pending: Dict[int, int] = {}              # user_id -> order_id (pending)
user_last_action_ts: Dict[int, float] = {}     # user_id -> last action timestamp
promo_codes: Dict[str, Dict[str, Any]] = {}    # code -> {"percent": int, "uses": int}
referrals: Dict[int, int] = {}                 # user_id -> referrer_id
user_orders: Dict[int, list] = {}              # user_id -> list of order_ids

# ---------------- Conversation states ----------------
LANG, CHOOSE_FLOW, AMOUNT, WALLET_TYPE, WALLET_INPUT, SCREENSHOT = range(6)

# ---------------- Multilang messages ----------------
MESSAGES = {
    "start": {
        "en": "Welcome!\nPlease select your language:",
        "ps": "ښه راغلاست!\nمهرباني وکړئ خپله ژبه وټاکئ:",
        "fa": "خوش آمدید!\nلطفاً زبان خود را انتخاب کنید:"
    },
    "choose_flow": {
        "en": "Do you want to Buy or Sell USDT?",
        "ps": "ایا تاسو USDT غواړئ وپېرئ یا وپلورئ؟",
        "fa": "می‌خواهید USDT بخرید یا بفروشید؟"
    },
    "ask_amount": {
        "en": "Choose a quick amount or type a custom USDT amount:",
        "ps": "یو مقدار انتخاب کړئ یا خپله اندازه ولیکئ:",
        "fa": "یک مقدار انتخاب کنید یا مقدار دلخواه را وارد کنید:"
    },
    "choose_wallet_type": {
        "en": "Choose wallet type (how you will receive/send):",
        "ps": "د والټ ډول انتخاب کړئ:",
        "fa": "نوع کیف پول را انتخاب کنید:"
    },
    "ask_wallet_binance": {
        "en": "Please enter your Binance ID:",
        "ps": "مهرباني وکړئ خپل Binance ID داخل کړئ:",
        "fa": "لطفاً شناسه Binance خود را وارد کنید:"
    },
    "ask_wallet_trc20": {
        "en": "Please enter your TRC20 wallet address:",
        "ps": "مهرباني وکړئ د TRC20 والټ آدرس داخل کړئ:",
        "fa": "لطفاً آدرس کیف پول TRC20 خود را وارد کنید:"
    },
    "payment_instructions_buy": {
        "en": (
            "💵 Payment Instructions\n"
            "------------------------\n"
            "• Total USD: {usd:.2f}\n"
            "• Total AFN: {afn:.2f} (Rate: {rate})\n\n"
            "Please send payment via HesabPay to ID: {hesab}\n\n"
            "After sending, upload your payment screenshot."
        ),
        "ps": (
            "💵 د تادیې لارښوونې\n"
            "------------------------\n"
            "• ټول USD: {usd:.2f}\n"
            "• ټول AFN: {afn:.2f} (نرخ: {rate})\n\n"
            "مهرباني وکړئ پیسې HesabPay ته ولیږئ: {hesab}\n\n"
            "د لیږلو وروسته خپل سکرین شاټ اپلوډ کړئ."
        ),
        "fa": (
            "💵 راهنمای پرداخت\n"
            "------------------------\n"
            "• مجموع USD: {usd:.2f}\n"
            "• مجموع AFN: {afn:.2f} (نرخ: {rate})\n\n"
            "پرداخت را از طریق HesabPay به این آی‌دی ارسال کنید: {hesab}\n\n"
            "پس از ارسال، اسکرین‌شات پرداخت را ارسال کنید."
        )
    },
    "payment_instructions_sell": {
        "en": (
            "🔁 Sell Instructions\n"
            "------------------------\n"
            "• Amount (USDT): {usd:.2f}\n"
            "• You will receive (AFN): {afn:.2f}\n\n"
            "Send USDT to our wallet (ask admin for the receiving address) and upload screenshot."
        ),
        "ps": (
            "🔁 د پلور لارښوونې\n"
            "------------------------\n"
            "• مقدار (USDT): {usd:.2f}\n"
            "• تاسو به ترلاسه کړئ (AFN): {afn:.2f}\n\n"
            "لطفاً USDT زموږ والټ ته واستوئ (د ترلاسه کولو پته د مدیر څخه وپوښتئ) او سکرین شاټ اپلوډ کړئ."
        ),
        "fa": (
            "🔁 دستورالعمل فروش\n"
            "------------------------\n"
            "• مقدار (USDT): {usd:.2f}\n"
            "• دریافت خواهید کرد (AFN): {afn:.2f}\n\n"
            "USDT را به کیف ما ارسال کنید (آدرس از مدیر گرفته شود) و اسکرین‌شات آپلود کنید."
        )
    },
    "ask_screenshot": {
        "en": "Upload the payment screenshot:",
        "ps": "د تادیې سکرین شاټ اپلوډ کړئ:",
        "fa": "اسکرین‌شات پرداخت را ارسال کنید:"
    },
    "order_pending_user": {
        "en": "✅ Your order is pending approval. Order ID: {id}",
        "ps": "ستاسو فرمایش د تایید لپاره روان دی. د فرمایش آی‌دی: {id}",
        "fa": "سفارش شما در انتظار تایید است. شناسه سفارش: {id}"
    },
    "no_pending": {
        "en": "You have no pending orders.",
        "ps": "تاسو هیڅ روان فرمایش نلرئ.",
        "fa": "شما سفارش معلقی ندارید."
    },
    "rate_updated": {
        "en": "AFN rate updated: {rate}",
        "ps": "د افغانی نرخ نوي شو: {rate}",
        "fa": "نرخ افغان جدید شد: {rate}"
    }
}

# ---------------- Helper utilities ----------------
def rate_limiter(user_id: int) -> bool:
    """Return True if allowed, False if action too soon."""
    now = time.time()
    last = user_last_action_ts.get(user_id, 0)
    if now - last < MIN_ACTION_SECONDS:
        return False
    user_last_action_ts[user_id] = now
    return True

def new_order_id() -> int:
    global _next_order_id
    oid = _next_order_id
    _next_order_id += 1
    return oid

def fetch_usd_to_afn_rate() -> float:
    """Fetch USD->AFN using exchangerate.host. Return current AFN rate or keep existing."""
    try:
        resp = requests.get("https://api.exchangerate.host/latest?base=USD&symbols=AFN", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            rate = float(data["rates"]["AFN"])
            logger.info("Fetched live AFN rate: %s", rate)
            return rate
    except Exception as e:
        logger.exception("Failed to fetch live rate: %s", e)
    return AFN_RATE

# ---------------- Background tasks ----------------
async def periodic_rate_updater(app):
    global AFN_RATE
    if LIVE_RATE_INTERVAL_MIN <= 0:
        return
    while True:
        try:
            rate = fetch_usd_to_afn_rate()
            AFN_RATE = rate
            logger.info("AFN_RATE updated to %s by periodic task", AFN_RATE)
        except Exception as e:
            logger.exception("Rate updater error: %s", e)
        await asyncio.sleep(LIVE_RATE_INTERVAL_MIN * 60)

async def daily_report_task(app):
    """Send daily summary to admin at DAILY_REPORT_TIME_UTC."""
    while True:
        now = datetime.utcnow()
        hh, mm = map(int, DAILY_REPORT_TIME_UTC.split(":"))
        next_run = datetime(now.year, now.month, now.day, hh, mm)
        if next_run <= now:
            next_run += timedelta(days=1)
        wait_seconds = (next_run - now).total_seconds()
        await asyncio.sleep(wait_seconds)
        try:
            # Build report
            total_orders = len(orders)
            pending = [o for o in orders.values() if o["status"] == "pending"]
            approved = [o for o in orders.values() if o["status"] == "approved"]
            rejected = [o for o in orders.values() if o["status"] == "rejected"]

            text = (
                f"📈 Daily Report ({next_run.date()} UTC)\n\n"
                f"Total orders: {total_orders}\n"
                f"Pending: {len(pending)}\n"
                f"Approved: {len(approved)}\n"
                f"Rejected: {len(rejected)}\n"
                f"Current AFN rate: {AFN_RATE}"
            )
            await app.bot.send_message(chat_id=ADMIN_ID, text=text)
        except Exception as e:
            logger.exception("Daily report failed: %s", e)
        # loop to next day automatically

# ---------------- Bot handlers ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rate_limiter(update.message.from_user.id):
        return
    keyboard = [[KeyboardButton("English"), KeyboardButton("Pashto"), KeyboardButton("Dari")]]
    await update.message.reply_text(MESSAGES["start"]["en"], reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return LANG

async def select_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rate_limiter(update.message.from_user.id):
        return
    text = update.message.text.lower()
    lang = "en" if "english" in text else "ps" if "pashto" in text else "fa"
    user_id = update.message.from_user.id
    user_data_store[user_id] = {"lang": lang}
    # ask buy or sell
    keyboard = [["Buy USDT"], ["Sell USDT"]]
    await update.message.reply_text(MESSAGES["choose_flow"][lang], reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return CHOOSE_FLOW

async def choose_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rate_limiter(update.message.from_user.id):
        return
    user_id = update.message.from_user.id
    lang = user_data_store[user_id]["lang"]
    flow = update.message.text.lower()
    if user_pending.get(user_id):
        await update.message.reply_text("You have a pending order. Please wait until it's processed.")
        return ConversationHandler.END
    context.user_data["flow"] = "buy" if "buy" in flow else "sell"
    # amount buttons
    buttons = [
        ["10", "20", "30", "40", "50"],
        ["60", "70", "80", "90", "100"],
        ["Custom Amount"]
    ]
    await update.message.reply_text(MESSAGES["ask_amount"][lang], reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True))
    return AMOUNT

async def amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rate_limiter(update.message.from_user.id):
        return
    user_id = update.message.from_user.id
    lang = user_data_store[user_id]["lang"]
    text = update.message.text
    if text.lower() == "custom amount":
        await update.message.reply_text("Enter amount (USDT):" if lang=="en" else "خپل مقدار ولیکئ:" if lang=="ps" else "مقدار را وارد کنید:")
        return AMOUNT
    try:
        amount = float(text)
    except:
        await update.message.reply_text(MESSAGES["ask_amount"][lang])
        return AMOUNT

    commission = compute_commission(amount)
    total_usd = round(amount + commission, 2)
    total_afn = round(total_usd * AFN_RATE, 2)

    # create pending order data in user_data_store
    user_data_store[user_id].update({
        "amount": amount,
        "commission": commission,
        "total_usd": total_usd,
        "total_afn": total_afn,
    })

    # wallet type
    keyboard = [["Binance ID", "TRC20 Wallet"]]
    await update.message.reply_text(MESSAGES["choose_wallet_type"][lang], reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return WALLET_TYPE

async def wallet_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rate_limiter(update.message.from_user.id):
        return
    user_id = update.message.from_user.id
    lang = user_data_store[user_id]["lang"]
    text = update.message.text.lower()
    if "binance" in text:
        user_data_store[user_id]["wallet_type"] = "binance"
        await update.message.reply_text(MESSAGES["ask_wallet_binance"][lang])
    else:
        user_data_store[user_id]["wallet_type"] = "trc20"
        await update.message.reply_text(MESSAGES["ask_wallet_trc20"][lang])
    return WALLET_INPUT

async def wallet_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rate_limiter(update.message.from_user.id):
        return
    user_id = update.message.from_user.id
    lang = user_data_store[user_id]["lang"]
    wallet_text = update.message.text.strip()
    user_data_store[user_id]["wallet"] = wallet_text

    flow = context.user_data.get("flow", "buy")
    if flow == "buy":
        # show payment instructions
        txt = MESSAGES["payment_instructions_buy"][lang].format(
            usd=user_data_store[user_id]["total_usd"],
            afn=user_data_store[user_id]["total_afn"],
            rate=AFN_RATE,
            hesab=HESABPAY_ID
        )
    else:
        txt = MESSAGES["payment_instructions_sell"][lang].format(
            usd=user_data_store[user_id]["amount"],
            afn=user_data_store[user_id]["total_afn"]
        )
    await update.message.reply_text(txt, parse_mode="Markdown")
    await update.message.reply_text(MESSAGES["ask_screenshot"][lang])
    return SCREENSHOT

async def screenshot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rate_limiter(update.message.from_user.id):
        return
    user_id = update.message.from_user.id
    if not update.message.photo:
        lang = user_data_store[user_id]["lang"]
        await update.message.reply_text(MESSAGES["ask_screenshot"][lang])
        return SCREENSHOT

    file_id = update.message.photo[-1].file_id
    # create order
    oid = new_order_id()
    order = {
        "id": oid,
        "user_id": user_id,
        "username": update.message.from_user.username,
        "flow": context.user_data.get("flow", "buy"),
        "amount": user_data_store[user_id]["amount"],
        "commission": user_data_store[user_id]["commission"],
        "total_usd": user_data_store[user_id]["total_usd"],
        "total_afn": user_data_store[user_id]["total_afn"],
        "wallet": user_data_store[user_id]["wallet"],
        "wallet_type": user_data_store[user_id]["wallet_type"],
        "screenshot": file_id,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat()
    }
    orders[oid] = order
    user_pending[user_id] = oid
    user_orders.setdefault(user_id, []).append(oid)

    # send to admin with buttons
    caption = (
        f"📦 New Order #{oid}\n\n"
        f"👤 @{order['username']} ({order['user_id']})\n"
        f"🔁 {order['flow'].upper()}\n"
        f"💰 {order['amount']} USDT\n"
        f"💵 Total: {order['total_usd']} USD / {order['total_afn']} AFN\n"
        f"🏦 Wallet: {order['wallet']} ({order['wallet_type']})\n"
        f"Created: {order['created_at']}"
    )
    buttons = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve:{oid}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject:{oid}")
        ]
    ]
    await context.bot.send_photo(chat_id=ADMIN_ID, photo=file_id, caption=caption, parse_mode="Markdown",
                                 reply_markup=InlineKeyboardMarkup(buttons))

    lang = user_data_store[user_id]["lang"]
    await update.message.reply_text(MESSAGES["order_pending_user"][lang].format(id=oid))
    return ConversationHandler.END

# ---------------- Admin callback actions ----------------
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("admin_approve:"):
        oid = int(data.split(":")[1])
        order = orders.get(oid)
        if not order:
            await query.edit_message_caption("Order not found")
            return
        if order["status"] != "pending":
            await query.edit_message_caption(f"Order already {order['status']}")
            return
        order["status"] = "approved"
        order["processed_at"] = datetime.utcnow().isoformat()
        # notify user
        uid = order["user_id"]
        lang = user_data_store.get(uid, {}).get("lang", "en")
        await context.bot.send_message(chat_id=uid, text=MESSAGES["approved_user"][lang])
        await query.edit_message_caption(query.message.caption + "\n\n✅ Approved")
        # clear pending
        user_pending.pop(uid, None)
        # offer buy again button
        try:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Buy Again", callback_data=f"buyagain:{uid}")]])
            await context.bot.send_message(chat_id=uid, text="Would you like to buy again?", reply_markup=kb)
        except Exception:
            pass

    elif data.startswith("admin_reject:"):
        oid = int(data.split(":")[1])
        order = orders.get(oid)
        if not order:
            await query.edit_message_caption("Order not found")
            return
        order["status"] = "rejected"
        order["processed_at"] = datetime.utcnow().isoformat()
        uid = order["user_id"]
        lang = user_data_store.get(uid, {}).get("lang", "en")
        await context.bot.send_message(chat_id=uid, text=MESSAGES["rejected_user"][lang])
        await query.edit_message_caption(query.message.caption + "\n\n❌ Rejected")
        user_pending.pop(uid, None)

    elif data.startswith("buyagain:"):
        uid = int(data.split(":")[1])
        # send message to user to start new buy
        lang = user_data_store.get(uid, {}).get("lang", "en")
        buttons = [["Buy USDT"], ["Sell USDT"]]
        await context.bot.send_message(chat_id=uid, text="Choose action:", reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True))
    else:
        await query.answer("Unknown action")

# ---------------- Admin commands & utilities ----------------
async def cmd_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return
    lines = []
    for oid, o in orders.items():
        lines.append(f"#{oid} {o['flow']} {o['amount']}USDT {o['total_usd']}$ {o['status']}")
    text = "Orders:\n" + ("\n".join(lines) if lines else "No orders")
    await update.message.reply_text(text)

async def cmd_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return
    pend = [o for o in orders.values() if o["status"] == "pending"]
    if not pend:
        await update.message.reply_text("No pending orders")
        return
    lines = [f"#{o['id']} @{o['username']} {o['amount']}USDT {o['total_usd']}$" for o in pend]
    await update.message.reply_text("\n".join(lines))

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    args = context.args
    if args and update.message.from_user.id == ADMIN_ID:
        # admin querying specific order
        try:
            oid = int(args[0])
            o = orders.get(oid)
            if not o:
                await update.message.reply_text("Order not found")
                return
            await update.message.reply_text(str(o))
            return
        except:
            await update.message.reply_text("Usage: /status <order_id>")
            return
    # user check own latest
    u_orders = user_orders.get(user_id, [])
    if not u_orders:
        await update.message.reply_text(MESSAGES["no_pending"]["en"])  # english fallback
        return
    last = orders[u_orders[-1]]
    await update.message.reply_text(str(last))

async def cmd_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global AFN_RATE
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Only admin can set rate")
        return
    args = context.args
    if not args:
        await update.message.reply_text(f"Current AFN rate: {AFN_RATE}")
        return
    if args[0].lower() == "live":
        r = fetch_usd_to_afn_rate()
        AFN_RATE = r
        await update.message.reply_text(MESSAGES["rate_updated"]["en"].format(rate=AFN_RATE))
        return
    try:
        AFN_RATE = float(args[0])
        await update.message.reply_text(MESSAGES["rate_updated"]["en"].format(rate=AFN_RATE))
    except:
        await update.message.reply_text("Usage: /rate <number> or /rate live")

# ---------------- Promo & Referral ----------------
async def cmd_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # admin can add: /promo add CODE percent
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Only admin")
        return
    args = context.args
    if not args:
        # list
        if not promo_codes:
            await update.message.reply_text("No promo codes")
            return
        lines = [f"{c}: {v['percent']}% uses:{v.get('uses',0)}" for c, v in promo_codes.items()]
        await update.message.reply_text("\n".join(lines))
        return
    if args[0] == "add" and len(args) >= 3:
        code = args[1].upper()
        try:
            pct = int(args[2])
        except:
            await update.message.reply_text("Percent must be integer")
            return
        promo_codes[code] = {"percent": pct, "uses": 0}
        await update.message.reply_text(f"Promo {code} added: {pct}%")
        return
    if args[0] == "remove" and len(args) >= 2:
        code = args[1].upper()
        promo_codes.pop(code, None)
        await update.message.reply_text(f"Removed {code}")
        return
    await update.message.reply_text("Usage: /promo (list)  or /promo add CODE PERCENT or /promo remove CODE")

async def cmd_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    code = f"REF{user_id}"
    await update.message.reply_text(f"Your referral code: {code}")

# ---------------- Startup ----------------
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_language)],
            CHOOSE_FLOW: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_flow)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_handler)],
            WALLET_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_type_handler)],
            WALLET_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_input_handler)],
            SCREENSHOT: [MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, screenshot_handler)],
        },
        fallbacks=[]
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(admin_callback))
    app.add_handler(CommandHandler("orders", cmd_orders))
    app.add_handler(CommandHandler("pending", cmd_pending))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("rate", cmd_rate))
    app.add_handler(CommandHandler("promo", cmd_promo))
    app.add_handler(CommandHandler("referral", cmd_referral))

    # start background tasks
    if LIVE_RATE_INTERVAL_MIN > 0:
        app.job_queue.run_repeating(lambda ctx: asyncio.create_task(update_rate_task(app)), interval=LIVE_RATE_INTERVAL_MIN*60, first=10)
    # Also start periodic tasks via asyncio.create_task
    loop = asyncio.get_event_loop()
    loop.create_task(periodic_rate_updater(app))
    loop.create_task(daily_report_task(app))

    logger.info("Bot started")
    app.run_polling()

# small helper to use within job_queue region (compatible)
async def update_rate_task(app):
    global AFN_RATE
    rate = fetch_usd_to_afn_rate()
    AFN_RATE = rate
    try:
        await app.bot.send_message(chat_id=ADMIN_ID, text=f"Live AFN rate updated: {AFN_RATE}")
    except Exception:
        pass

if __name__ == "__main__":
    main()
