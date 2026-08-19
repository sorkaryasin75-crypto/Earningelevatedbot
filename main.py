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

# --- ১. গ্লোবাল কনফিগারেশন ও ডাটা (ওয়েব অ্যাপ কোড অনুযায়ী) ---
BOT_TOKEN = "8868300612:AAH33rOPD7g-1s8dycSIdsNGZsOgZdPnqo0"  # আপনার টেলিগ্রাম বট টোকেন দিন
WEB_APP_URL = "https://economyshops.blogspot.com"  # আপনার ওয়েব অ্যাপ লিঙ্ক

# ওয়েব অ্যাপের ডিফল্ট কনফিগারেশন
COIN_CONFIGS = {
    "niva": {"label": "Niva Coin", "price": 5, "target": "@sell_point_it", "active": True},
    "NewTop": {"label": "NewTop Coin", "price": 3, "target": "@Send", "active": True},
    "topfollows": {"label": "topfollows", "price": 3, "target": "@topfollowsadmin", "active": True},
    "ns": {"label": "Ns Coin", "price": 8, "target": "@NsCoinAdmin", "active": True},
}

DEFAULT_FEE = 5
MIN_AMOUNT = 50000

# Logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# --- ২. মেনু তৈরি করার ফাংশনসমূহ ---

def get_main_keyboard():
    """প্রধান ইনলাইন কিবোর্ড মেনু"""
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
            # WebApp Button: টেলিগ্রামের ভেতরেই ওয়েব অ্যাপ খোলার বাটন
            InlineKeyboardButton("🌐 Open Full Web App", web_app=WebAppInfo(url=WEB_APP_URL))
        ],
        [
            InlineKeyboardButton("📢 Official Channel", url="https://t.me/EducationPointBD"),
            InlineKeyboardButton("👨‍💻 Support", url="https://t.me/educationpointbd24"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

# --- ৩. কমান্ড এবং কলব্যাক হ্যান্ডলার ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start কমান্ড দিলে মেইন মেনু দেখাবে"""
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
    """বাটনে ক্লিক করলে যা ঘটবে"""
    query = update.callback_query
    await query.answer()
    data = query.data

    # ১. মেইন মেনুতে ব্যাক
    if data == "main_menu":
        await start(update, context)

    # ২. লাইভ রেট দেখা
    elif data == "menu_rates":
        rates_text = "📊 **Live Market Rates (প্রতি ১০০০ কয়েন):**\n\n"
        for key, coin in COIN_CONFIGS.items():
            status = "✅ Active" if coin["active"] else "❌ Buy Stop"
            rates_text += f"• **{coin['label']}**: {coin['price']} ৳ ({status})\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]
        await query.edit_message_text(rates_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # ৩. কয়েন বিক্রির মেনু (Coin Selection)
    elif data == "menu_sell":
        keyboard = []
        for key, coin in COIN_CONFIGS.items():
            if coin["active"]:
                keyboard.append([InlineKeyboardButton(f"Sell {coin['label']} ({coin['price']}৳/1K)", callback_data=f"sell_{key}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")])
        
        sell_text = "🛒 **কোন কয়েনটি বিক্রি করতে চান বেছে নিন:**\n*(সর্বনিম্ন পরিমাণ: ৫০,০০০ কয়েন)*"
        await query.edit_message_text(sell_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # ৪. নির্দিষ্ট কয়েন সিলেক্ট করলে
    elif data.startswith("sell_"):
        coin_key = data.split("_")[1]
        coin = COIN_CONFIGS.get(coin_key)
        context.user_data["selected_coin"] = coin_key

        if coin_key == "topfollows":
            instruction = f"👉 কুপন কোড তৈরি করে রাখুন এবং অ্যাডমিন ইউজারনেমে পাঠান: `{coin['target']}`"
        else:
            instruction = f"👉 গেম থেকে এই ইউজারনেমে কয়েন ট্রান্সফার করুন: `{coin['target']}`"

        text = (
            f"✅ **আপনি বেছে নিয়েছেন: {coin['label']}**\n"
            f"💰 রেট: {coin['price']} ৳ (প্রতি ১,০০০০)\n"
            f"📌 ফি: {DEFAULT_FEE} ৳\n\n"
            f"{instruction}\n\n"
            "ধাপ ১: কত পরিমাণ কয়েন সেল করতে চান নিচে লিখুন (যেমন: 50000):"
        )
        
        # ইউজারের রেসপন্স নেওয়ার জন্য স্টেট সেট
        context.user_data["step"] = "AWAITING_AMOUNT"
        
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="menu_sell")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # ৫. লিডারবোর্ড
    elif data == "menu_leaderboard":
        lb_text = (
            "🏆 **Top Sellers Leaderboard**\n\n"
            "🥇 1. User_982 - 45 Sells\n"
            "🥈 2. TradingKing - 32 Sells\n"
            "🥉 3. AlexBD - 28 Sells\n\n"
            "💡 সম্পূর্ণ লিডারবোর্ড দেখতে নিচের **Open Full Web App** বাটনটি ব্যবহার করুন।"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]
        await query.edit_message_text(lb_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # ৬. হিস্ট্রি
    elif data == "menu_history":
        history_text = (
            "📜 **আপনার সাম্প্রতিক লেনদেন:**\n\n"
            "• Niva Coin | 50K | 245 ৳ | ✅ Accepted\n"
            "• Ns Coin | 100K | 795 ৳ | ⏳ Pending\n"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]
        await query.edit_message_text(history_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- ৪. ইউজারের ডাটা ইনপুট প্রসেস (অ্যামাউন্ট ও নগদ নম্বর নেওয়া) ---

async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ইউজার টেক্সট মেসেজ পাঠালে তা প্রসেস করা"""
    step = context.user_data.get("step")
    
    if not step:
        return

    # পরিমাণ ইনপুট নেওয়া
    if step == "AWAITING_AMOUNT":
        try:
            amount = int(update.message.text.strip())
            if amount < MIN_AMOUNT:
                await update.message.reply_text(f"⚠️ সর্বনিম্ন পরিমাণ {MIN_AMOUNT} কয়েন। আবার চেষ্টা করুন:")
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
            await update.message.reply_text("⚠️ অনুগ্রহ করে সঠিক সংখ্যা লিখুন (যেমন: 50000):")

    # ইউজারনেম / কুপন কোড ইনপুট নেওয়া
    elif step in ["AWAITING_SENDER", "AWAITING_COUPON"]:
        context.user_data["sender_info"] = update.message.text.strip()
        context.user_data["step"] = "AWAITING_NAGAD"
        await update.message.reply_text("ধাপ ৩: পেমেন্ট নেওয়ার জন্য আপনার **নগদ (Nagad)** নম্বরটি দিন:")

    # নগদ নম্বর নেওয়া এবং রিকোয়েস্ট নিশ্চিত করা
    elif step == "AWAITING_NAGAD":
        nagad_number = update.message.text.strip()
        coin_key = context.user_data["selected_coin"]
        coin = COIN_CONFIGS[coin_key]
        amount = context.user_data["amount"]
        sender_info = context.user_data["sender_info"]
        
        # হিসাব কষা (Taka Calculation)
        amount_k = amount / 1000
        gross_taka = amount_k * coin["price"]
        net_taka = max(0, gross_taka - DEFAULT_FEE)
        
        # স্টেট ক্লিয়ার করা
        context.user_data["step"] = None

        summary_text = (
            "✅ **আপনার সেল রিকোয়েস্ট তৈরি হয়েছে!**\n\n"
            f"🔹 **কয়েন:** {coin['label']}\n"
            f"🔹 **পরিমাণ:** {amount_k}K ({amount} Coins)\n"
            f"🔹 **প্রেরক/কুপন:** `{sender_info}`\n"
            f"🔹 **নগদ নম্বর:** `{nagad_number}`\n"
            f"💰 **আপনি পাবেন:** `{net_taka} ৳` (ফি ৫৳ কাটার পর)\n\n"
            "⏳ অ্যাডমিন ভেরিফাই করে আপনার নগদ নম্বরে পেমেন্ট পাঠিয়ে দেবে।"
        )
        
        keyboard = [
            [InlineKeyboardButton("💬 Message Admin", url="https://t.me/educationpointbd24")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
        ]
        
        await update.message.reply_text(summary_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- ৫. মেইন রানার ---

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # হ্যান্ডলার রেজিস্টার
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))

    print("Earning Elevated Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
      
