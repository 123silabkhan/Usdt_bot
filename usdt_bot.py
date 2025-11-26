import os
import json
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton,
    ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

# ---------------------------
# JSON DATABASE FUNCTIONS
# ---------------------------
DATA_FILE = "db.json"

def load_db():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({"users": {}, "orders": []}, f)
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ---------------------------
# CONVERSATION STATES
# ---------------------------
REG_FIRST, REG_LAST, REG_METHOD, REG_WA = range(4)
ORDER_TYPE, ORDER_RATE, ORDER_ADDR = range(10, 13)
BUY_AMOUNT, BUY_ADDR, BUY_SCREENSHOT = range(20, 23)


ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))


# ---------------------------
# /start
# ---------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    btns = [
        ["Register as Seller", "Register as Buyer"],
        ["Create Order", "Buy USDT"]
    ]
    await update.message.reply_text(
        "Welcome to the USDT P2P Bot.\nChoose an option:",
        reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True)
    )


# ---------------------------
# REGISTRATION SECTION
# ---------------------------
async def register_start(update: Update, context):
    role = update.message.text.replace("Register as ", "")
    context.user_data["role"] = role
    await update.message.reply_text("Enter your *First Name*:")
    return REG_FIRST

async def reg_first(update, context):
    context.user_data["first"] = update.message.text
    await update.message.reply_text("Enter your *Last Name*:")
    return REG_LAST

async def reg_last(update, context):
    context.user_data["last"] = update.message.text
    await update.message.reply_text("Enter your Payment Method (Hesapay, etc):")
    return REG_METHOD

async def reg_method(update, context):
    context.user_data["method"] = update.message.text
    await update.message.reply_text("Enter your WhatsApp Number:")
    return REG_WA

async def reg_finish(update, context):
    wa = update.message.text
    data = load_db()
    user_id = str(update.message.from_user.id)

    data["users"][user_id] = {
        "first": context.user_data["first"],
        "last": context.user_data["last"],
        "method": context.user_data["method"],
        "wa": wa,
        "role": context.user_data["role"],
        "approved": False
    }

    save_db(data)

    # Notify admin
    await context.bot.send_message(
        ADMIN_CHAT_ID,
        f"New Registration Request:\n"
        f"Role: {context.user_data['role']}\n"
        f"Name: {context.user_data['first']} {context.user_data['last']}\n"
        f"Method: {context.user_data['method']}\n"
        f"WA: {wa}\n\n"
        f"Approve?\nUser ID: {user_id}"
    )

    await update.message.reply_text(
        "Registration submitted. Waiting for admin approval."
    )
    return ConversationHandler.END


# ---------------------------
# ADMIN APPROVAL COMMAND
# ---------------------------
async def approve(update: Update, context):
    if update.message.chat_id != ADMIN_CHAT_ID:
        return
    
    try:
        uid = context.args[0]
    except:
        await update.message.reply_text("Usage: /approve user_id")
        return
    
    data = load_db()
    if uid not in data["users"]:
        await update.message.reply_text("User not found.")
        return
    
    data["users"][uid]["approved"] = True
    save_db(data)

    await update.message.reply_text("Approved!")
    await context.bot.send_message(int(uid), "Your registration has been approved!")


# ---------------------------
# CREATE ORDER (Seller/Buyer)
# ---------------------------
async def create_order(update, context):
    data = load_db()
    uid = str(update.message.from_user.id)

    if uid not in data["users"] or not data["users"][uid]["approved"]:
        await update.message.reply_text("You must be registered & approved.")
        return ConversationHandler.END

    await update.message.reply_text(
        "Choose Order Type:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Sell USDT", callback_data="sell")],
            [InlineKeyboardButton("Buy USDT", callback_data="buy")]
        ])
    )
    return ORDER_TYPE

async def order_type(update, context):
    query = update.callback_query
    await query.answer()
    context.user_data["order_type"] = query.data
    await query.message.reply_text("Enter your rate (AFN per USDT):")
    return ORDER_RATE

async def order_rate(update, context):
    context.user_data["rate"] = update.message.text
    await update.message.reply_text("Enter your Binance ID or TRC20 address:")
    return ORDER_ADDR

async def order_finish(update, context):
    address = update.message.text
    data = load_db()
    uid = str(update.message.from_user.id)

    order = {
        "user_id": uid,
        "type": context.user_data["order_type"],
        "rate": context.user_data["rate"],
        "address": address
    }
    data["orders"].append(order)
    save_db(data)

    await update.message.reply_text("Order created successfully!")
    return ConversationHandler.END


# ---------------------------
# CUSTOMER BUY SECTION
# ---------------------------
async def buy_usdt(update, context):
    await update.message.reply_text("Enter amount of USDT you want to buy:")
    return BUY_AMOUNT

async def buy_amount(update, context):
    context.user_data["buy_amount"] = update.message.text
    await update.message.reply_text("Enter your Binance ID / TRC20 address:")
    return BUY_ADDR

async def buy_addr(update, context):
    context.user_data["buy_addr"] = update.message.text

    await update.message.reply_text(
        "Pay using *Hesapay* to the platform account and send screenshot."
    )
    return BUY_SCREENSHOT

async def buy_screenshot(update, context):
    photo = update.message.photo[-1].file_id

    await update.message.reply_text("Order received. We will process shortly.")

    # Send to admin / sellers
    await update.get_bot().send_photo(
        chat_id=ADMIN_CHAT_ID,
        photo=photo,
        caption=(
            "New BUY Request:\n"
            f"Amount: {context.user_data['buy_amount']} USDT\n"
            f"Address: {context.user_data['buy_addr']}"
        )
    )

    return ConversationHandler.END


# ---------------------------
# BOT SETUP
# ---------------------------
def main():
    token = os.getenv("TELEGRAM_TOKEN")
    app = ApplicationBuilder().token(token).build()

    # Registration Handler
    reg_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("Register as"), register_start)
        ],
        states={
            REG_FIRST: [MessageHandler(filters.TEXT, reg_first)],
            REG_LAST: [MessageHandler(filters.TEXT, reg_last)],
            REG_METHOD: [MessageHandler(filters.TEXT, reg_method)],
            REG_WA: [MessageHandler(filters.TEXT, reg_finish)],
        },
        fallbacks=[]
    )

    # Create Order Handler
    order_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("Create Order"), create_order)
        ],
        states={
            ORDER_TYPE: [CallbackQueryHandler(order_type)],
            ORDER_RATE: [MessageHandler(filters.TEXT, order_rate)],
            ORDER_ADDR: [MessageHandler(filters.TEXT, order_finish)],
        },
        fallbacks=[]
    )

    # Buy USDT Handler
    buy_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("Buy USDT"), buy_usdt)
        ],
        states={
            BUY_AMOUNT: [MessageHandler(filters.TEXT, buy_amount)],
            BUY_ADDR: [MessageHandler(filters.TEXT, buy_addr)],
            BUY_SCREENSHOT: [MessageHandler(filters.PHOTO, buy_screenshot)]
        },
        fallbacks=[]
    )

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approve", approve))

    # Add conversations
    app.add_handler(reg_conv)
    app.add_handler(order_conv)
    app.add_handler(buy_conv)

    app.run_polling()


if __name__ == "__main__":
    main()
