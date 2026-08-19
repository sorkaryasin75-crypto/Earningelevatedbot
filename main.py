import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# --- ১. কনফিগারেশন ---
BOT_TOKEN = "8312396498:AAF07jeC_2wJSxb1mVxfocwHEXJvCyz3DQ4"  # আপনার বট টোকেন দিন
ADMIN_TELEGRAM_ID = 6582650458  # আপনার টেলিগ্রাম UID
WEB_APP_URL = "https://economyshops.blogspot.com"

# ওয়েব অ্যাপ অনুযায়ী কয়েন কনফিগারেশন (মেমোরিতে সেভ থাকবে এবং এডমিন চেঞ্জ করতে পারবে)
COIN_CONFIGS = {
    "niva": {"label": "Niva Coin", "price": 5, "target": "@sell_point_it", "active": True},
    "NewTop": {"label": "NewTop Coin", "price": 3, "target": "@Send", "active": True},
    "topfollows": {"label": "topfollows", "price": 3, "target": "@topfollowsadmin", "active": True},
    "ns": {"label": "Ns Coin", "price": 8, "target": "@NsCoinAdmin", "active": True},
}

DEFAULT_FEE = 5
MIN_AMOUNT = 50000

# সাময়িকভাবে রিকোয়েস্ট ডাটা ট্র্যাকিংয়ের জন্য (Memory Store)
pending_requests = {}

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# --- ২. ইউজার মেনু কিবোর্ড ---

def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🛒 Sell Coins", callback_data="menu_sell"),
            InlineKeyboardButton("📊 Live Rates", callback_data="menu_rates"),
        ],
        [
            InlineKeyboardButton("🏆 Leaderboard", callback_data="menu_leaderboard"),
            InlineKeyboardButton("📜 My History", callback_data="menu_history"),
        ],
        [
            InlineKeyboardButton("🌐 Open Full Web App", web_app=WebAppInfo(url=WEB_APP_URL))
        ],
        [
            InlineKeyboardButton("📢 Official Channel", url="https://t.me/EducationPointBD"),
            InlineKeyboardButton("👨‍💻 Support", url="https://t.me/educationpointbd24"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

# --- ৩. /start ও ইউজার ফাংশনসমূহ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = (
        f"👋 **Earning Elevated**-এ আপনাকে স্বাগতম, {user.first_name}!\n\n"
        "এটি একটি নিরাপদ ও নির্ভরযোগ্য কয়েন বাই-সেল প্ল্যাটফর্ম। "
        "নিচের বাটনগুলো ব্যবহার করে খুব সহজেই লেনদেন করুন:"
    )
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "main_menu":
        await start(update, context)

    elif data == "menu_rates":
        rates_text = "📊 **Live Market Rates (প্রতি ১০০০ কয়েন):**\n\n"
        for key, coin in COIN_CONFIGS.items():
            status = "✅ Active" if coin["active"] else "❌ Buy Stop"
            rates_text += f"• **{coin['label']}**: {coin['price']} ৳ ({status})\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]
        await query.edit_message_text(rates_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "menu_sell":
        keyboard = []
        for key, coin in COIN_CONFIGS.items():
            if coin["active"]:
                keyboard.append([InlineKeyboardButton(f"Sell {coin['label']} ({coin['price']}৳/1K)", callback_data=f"sell_{key}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")])
        
        sell_text = "🛒 **কোন কয়েনটি বিক্রি করতে চান বেছে নিন:**\n*(সর্বনিম্ন পরিমাণ: ৫০,০০০ কয়েন)*"
        await query.edit_message_text(sell_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("sell_"):
        coin_key = data.split("_")[1]
        coin = COIN_CONFIGS.get(coin_key)
        context.user_data["selected_coin"] = coin_key

        if coin_key == "topfollows":
            instruction = f"👉 কুপন কোড তৈরি করে রাখুন এবং এডমিন ইউজারনেমে পাঠান: `{coin['target']}`"
        else:
            instruction = f"👉 গেম থেকে এই ইউজারনেমে কয়েন ট্রান্সফার করুন: `{coin['target']}`"

        text = (
            f"✅ **আপনি বেছে নিয়েছেন: {coin['label']}**\n"
            f"💰 রেট: {coin['price']} ৳ (প্রতি ১,০০০)\n"
            f"📌 ফি: {DEFAULT_FEE} ৳\n\n"
            f"{instruction}\n\n"
            "ধাপ ১: কত পরিমাণ কয়েন সেল করতে চান নিচে লিখুন (যেমন: 50000):"
        )
        context.user_data["step"] = "AWAITING_AMOUNT"
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="menu_sell")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # --- এডমিন অ্যাকশন (Accept / Reject) ---
    elif data.startswith("admin_accept_") or data.startswith("admin_reject_"):
        if user_id != ADMIN_TELEGRAM_ID:
            await query.answer("⚠️ আপনি এডমিন নন!", show_alert=True)
            return

        action, req_id = data.rsplit("_", 1)
        req_id = int(req_id)
        req = pending_requests.get(req_id)

        if not req:
            await query.edit_message_text(query.message.text + "\n\n⚠️ **এই রিকোয়েস্টটি আগেই প্রসেস করা হয়েছে।**")
            return

        target_user_id = req["user_id"]

        if action == "admin_accept":
            # এডমিন একসেপ্ট করলে ইউজারকে মেসেজ
            user_msg = (
                "✅ **আপনার কয়েন সেল রিকোয়েস্ট সফলভাবে একসেপ্ট করা হয়েছে!**\n\n"
                f"💰 **টাকা:** {req['net_taka']} ৳\n"
                f"📱 **নগদ নম্বর:** `{req['nagad_number']}`\n"
                "আপনার নগদ নম্বরে পেমেন্ট সফলভাবে পাঠানো হয়েছে। Earning Elevated-এর সাথে থাকার জন্য ধন্যবাদ!"
            )
            await context.bot.send_message(chat_id=target_user_id, text=user_msg, parse_mode="Markdown")
            await query.edit_message_text(query.message.text + "\n\n✅ **ACCEPTED and Payment Status Sent to User!**")

        elif action == "admin_reject":
            # এডমিন রিজেক্ট করলে ইউজারকে মেসেজ
            user_msg = (
                "❌ **আপনার কয়েন সেল রিকোয়েস্টটি বাতিল (Rejected) করা হয়েছে।**\n\n"
                "সম্ভাব্য কারণ: কয়েন ট্রান্সফার/কুপন কোড ভেরিফিকেশন ব্যর্থ হয়েছে। "
                "যেকোনো সমস্যায় এডমিনের সাথে যোগাযোগ করুন: @educationpointbd24"
            )
            await context.bot.send_message(chat_id=target_user_id, text=user_msg, parse_mode="Markdown")
            await query.edit_message_text(query.message.text + "\n\n❌ **REJECTED and User Notified.**")

        # মেমোরি থেকে রিকোয়েস্ট রিমুভ করা
        del pending_requests[req_id]

    # --- এডমিন প্রাইস চেঞ্জ মেনু ---
    elif data.startswith("change_price_"):
        if user_id != ADMIN_TELEGRAM_ID:
            return
        coin_key = data.split("_")[2]
        context.user_data["admin_step"] = "AWAITING_NEW_PRICE"
        context.user_data["admin_coin"] = coin_key
        await query.edit_message_text(f"✏️ **{COIN_CONFIGS[coin_key]['label']}**-এর নতুন দাম প্রতি ১০০০ কয়েনের জন্য কত দিতে চান? (সংখ্যা লিখুন):", parse_mode="Markdown")

# --- ৪. ইউজার ইনপুট ও সেল রিকোয়েস্ট এডমিনের কাছে পাঠানো ---

async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    step = context.user_data.get("step")
    admin_step = context.user_data.get("admin_step")

    # --- এডমিন প্রাইস আপডেট প্রসেস ---
    if user_id == ADMIN_TELEGRAM_ID and admin_step == "AWAITING_NEW_PRICE":
        try:
            new_price = float(text)
            coin_key = context.user_data.get("admin_coin")
            COIN_CONFIGS[coin_key]["price"] = new_price
            context.user_data["admin_step"] = None
            await update.message.reply_text(f"✅ **{COIN_CONFIGS[coin_key]['label']}**-এর দাম সফলভাবে আপডেট করা হয়েছে: `{new_price} ৳`", parse_mode="Markdown")
            return
        except ValueError:
            await update.message.reply_text("⚠️ অনুগ্রহ করে সঠিক দাম লিখুন (যেমন: 6.5):")
            return

    if not step:
        return

    # ১. অ্যামাউন্ট নেওয়া
    if step == "AWAITING_AMOUNT":
        try:
            amount = int(text)
            if amount < MIN_AMOUNT:
                await update.message.reply_text(f"⚠️ সর্বনিম্ন পরিমাণ {MIN_AMOUNT} কয়েন। আবার লিখুন:")
                return
            context.user_data["amount"] = amount
            coin_key = context.user_data["selected_coin"]

            if coin_key == "topfollows":
                context.user_data["step"] = "AWAITING_COUPON"
                await update.message.reply_text("ধাপ ২: আপনার **Topfollows Coupon Code** টি লিখুন:")
            else:
                context.user_data["step"] = "AWAITING_SENDER"
                await update.message.reply_text("ধাপ ২: আপনি যে ইউজারনেম/আইডি থেকে কয়েন পাঠিয়েছেন তা লিখুন:")
        except ValueError:
            await update.message.reply_text("⚠️ অনুগ্রহ করে সংখ্যা লিখুন (যেমন: 50000):")

    # ২. ইউজারনেম/কুপন নেওয়া
    elif step in ["AWAITING_SENDER", "AWAITING_COUPON"]:
        context.user_data["sender_info"] = text
        context.user_data["step"] = "AWAITING_NAGAD"
        await update.message.reply_text("ধাপ ৩: পেমেন্ট নেওয়ার জন্য আপনার **নগদ (Nagad)** নম্বরটি দিন:")

    # ৩. নগদ নম্বর ও এডমিনের কাছে সেল রিকোয়েস্ট পাঠানো
    elif step == "AWAITING_NAGAD":
        nagad_number = text
        coin_key = context.user_data["selected_coin"]
        coin = COIN_CONFIGS[coin_key]
        amount = context.user_data["amount"]
        sender_info = context.user_data["sender_info"]

        amount_k = amount / 1000
        gross_taka = amount_k * coin["price"]
        net_taka = max(0, gross_taka - DEFAULT_FEE)

        context.user_data["step"] = None

        # ইউজারের কাছে মেসেজ
        await update.message.reply_text(
            "⏳ **আপনার রিকোয়েস্টটি সাবমিট হয়েছে!**\n\n"
            "এডমিন কয়েন ভেরিফাই করে পেমেন্ট পাঠিয়ে দেবে এবং আপনাকে জানিয়ে দেওয়া হবে।",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )

        # ইউনিক রিকোয়েস্ট আইডি
        req_id = update.message.message_id
        pending_requests[req_id] = {
            "user_id": user_id,
            "user_name": update.effective_user.first_name,
            "username": update.effective_user.username or "N/A",
            "coin_label": coin["label"],
            "amount": amount,
            "sender_info": sender_info,
            "nagad_number": nagad_number,
            "net_taka": net_taka,
        }

        # --- এডমিন বক্সে পুরো ডাটা পাঠানো ---
        admin_notice = (
            "🚨 **নতুন কয়েন সেল রিকোয়েস্ট এসেছে!**\n\n"
            f"👤 **ইউজার:** {update.effective_user.first_name} (@{update.effective_user.username or 'N/A'})\n"
            f"🆔 **Telegram UID:** `{user_id}`\n"
            f"🪙 **কয়েন:** {coin['label']}\n"
            f"📦 **পরিমাণ:** {amount_k}K ({amount})\n"
            f"📩 **প্রেরক/কুপন:** `{sender_info}`\n"
            f"📱 **নগদ নম্বর:** `{nagad_number}`\n"
            f"💰 **পেমেন্ট করতে হবে:** `{net_taka} ৳`\n\n"
            "⚠️ আসল নাকি নকল ভেরিফাই করে নিচে বাটন চাপুন:"
        )

        admin_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Accept & Pay", callback_data=f"admin_accept_{req_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_{req_id}"),
            ]
        ])

        await context.bot.send_message(chat_id=ADMIN_TELEGRAM_ID, text=admin_notice, reply_markup=admin_keyboard, parse_mode="Markdown")

# --- ৫. এডমিন প্যানেল কমান্ড (`/admin`) ---

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_TELEGRAM_ID:
        await update.message.reply_text("❌ আপনি এডমিন নন।")
        return

    admin_text = "⚙️ **Admin Panel - Earning Elevated**\n\nকোন কয়েনের দাম পরিবর্তন করতে চান বেছে নিন:"
    keyboard = []
    for key, coin in COIN_CONFIGS.items():
        keyboard.append([InlineKeyboardButton(f"✏️ {coin['label']} ({coin['price']}৳)", callback_data=f"change_price_{key}")])

    await update.message.reply_text(admin_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- ৬. মেইন বোটিং ---

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))  # এডমিন প্যানেল কমান্ড
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))

    print("Earning Elevated Admin Bot is Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
        
