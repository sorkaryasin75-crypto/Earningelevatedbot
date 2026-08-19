import logging
import os
import threading
import time
import requests
from flask import Flask
import firebase_admin
from firebase_admin import credentials, db
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
BOT_TOKEN = "8312396498:AAF07jeC_2wJSxb1mVxfocwHEXJvCyz3DQ4"  # আপনার টেলিগ্রাম বট টোকেন দিন
ADMIN_TELEGRAM_ID = 6582650458  # আপনার টেলিগ্রাম UID
WEB_APP_URL = "https://economyshops.blogspot.com"
RENDER_APP_URL = "https://earningelevatedbot.onrender.com"  # Render থেকে পাওয়া URL এখানে দিন

# --- ২. FIREBASE ইনিশিয়ালাইজেশন ---
# firebase-key.json ফাইলটি প্রজেক্ট ফোল্ডারে রাখুন
cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://sell-point-it-default-rtdb.firebaseio.com'  # আপনার ফায়ারবেস ডেটাবেজ URL
})

# কয়েনের প্রাথমিক মান ফায়ারবেজে সেভ না থাকলে সেট করার জন্য
DEFAULT_COINS = {
    "niva": {"label": "Niva Coin", "price": 4.65, "target": "@sell_point_it", "active": True},
    "newtopfollow": {"label": "New Topfollow", "price": 4.20, "target": "@Send", "active": True},
    "oldtopfollow": {"label": "Old Topfollow", "price": 4.70, "target": "@topfollowsadmin", "active": True},
    "nsfollow": {"label": "NS Follow", "price": 12.0, "target": "@NsCoinAdmin", "active": True},
}

# ফায়ারবেসে কয়েন ডাটা সেটআপ বা লোড করা
coins_ref = db.reference('coin_configs')
if not coins_ref.get():
    coins_ref.set(DEFAULT_COINS)

DEFAULT_FEE = 5
MIN_AMOUNT = 50000

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# --- ৩. RENDER SLEEP MODE FIX (FLASK WEB SERVER & SELF PING) ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Earning Elevated Bot is Alive & Running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

def keep_alive():
    """স্বয়ংক্রিয় পিন দিয়ে বটকে ঘুমিয়ে পড়া থেকে বাঁচাবে"""
    while True:
        time.sleep(300) # ৫ মিনিট পর পর পিন করবে
        try:
            requests.get(RENDER_APP_URL)
            print("Self ping successful!")
        except Exception as e:
            print(f"Self ping failed: {e}")

# --- ৪. ইউজার কিবোর্ড ---
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

# --- ৫. মূল বোটিং লজিক ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # ফায়ারবেসে ইউজার প্রোফাইল সেভ/আপডেট
    db.reference(f'users/{user.id}').update({
        'telegramName': user.first_name,
        'telegramUsername': user.username or "N/A",
        'lastSeen': int(time.time())
    })

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
    
    coins_data = db.reference('coin_configs').get() or DEFAULT_COINS

    if data == "main_menu":
        await start(update, context)

    elif data == "menu_rates":
        rates_text = "📊 **Live Market Rates (প্রতি ১০০০ কয়েন):**\n\n"
        for key, coin in coins_data.items():
            status = "✅ Active" if coin.get("active", True) else "❌ Buy Stop"
            rates_text += f"• **{coin['label']}**: {coin['price']} ৳ ({status})\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]
        await query.edit_message_text(rates_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "menu_sell":
        keyboard = []
        for key, coin in coins_data.items():
            if coin.get("active", True):
                keyboard.append([InlineKeyboardButton(f"Sell {coin['label']} ({coin['price']}৳/1K)", callback_data=f"sell_{key}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")])
        sell_text = "🛒 **কোন কয়েনটি বিক্রি করতে চান বেছে নিন:**\n*(সর্বনিম্ন পরিমাণ: ৫০,০০০ কয়েন)*"
        await query.edit_message_text(sell_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("sell_"):
        coin_key = data.split("_")[1]
        coin = coins_data.get(coin_key)
        context.user_data["selected_coin"] = coin_key

        if "topfollow" in coin_key:
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
        req_ref = db.reference(f'requests/{req_id}')
        req = req_ref.get()

        if not req or req.get("status") != "Pending":
            await query.edit_message_text(query.message.text + "\n\n⚠️ **এই রিকোয়েস্টটি আগেই প্রসেস করা হয়েছে।**")
            return

        target_user_id = req["user_id"]

        if action == "admin_accept":
            req_ref.update({"status": "Accepted", "processedAt": int(time.time())})
            
            user_msg = (
                "✅ **আপনার কয়েন সেল রিকোয়েস্ট সফলভাবে একসেপ্ট করা হয়েছে!**\n\n"
                f"💰 **টাকা:** {req['net_taka']} ৳\n"
                f"📱 **নগদ নম্বর:** `{req['nagad_number']}`\n"
                "আপনার নগদ নম্বরে পেমেন্ট সফলভাবে পাঠানো হয়েছে।"
            )
            await context.bot.send_message(chat_id=target_user_id, text=user_msg, parse_mode="Markdown")
            await query.edit_message_text(query.message.text + "\n\n✅ **ACCEPTED & Saved to Firebase!**")

        elif action == "admin_reject":
            req_ref.update({"status": "Rejected", "processedAt": int(time.time())})
            
            user_msg = (
                "❌ **আপনার কয়েন সেল রিকোয়েস্টটি বাতিল (Rejected) করা হয়েছে।**\n\n"
                "সম্ভাব্য কারণ: কয়েন ট্রান্সফার/কুপন কোড ভেরিফিকেশন ব্যর্থ হয়েছে।"
            )
            await context.bot.send_message(chat_id=target_user_id, text=user_msg, parse_mode="Markdown")
            await query.edit_message_text(query.message.text + "\n\n❌ **REJECTED & Saved to Firebase!**")

    # --- এডমিন প্রাইস চেঞ্জ ---
    elif data.startswith("change_price_"):
        if user_id != ADMIN_TELEGRAM_ID:
            return
        coin_key = data.split("_")[2]
        context.user_data["admin_step"] = "AWAITING_NEW_PRICE"
        context.user_data["admin_coin"] = coin_key
        await query.edit_message_text(f"✏️ **{coins_data[coin_key]['label']}**-এর নতুন দাম লিখুন:", parse_mode="Markdown")

# --- ৬. ইউজারের ইনপুট এবং ফায়ারবেসে রিকোয়েস্ট সেভ ---
async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    step = context.user_data.get("step")
    admin_step = context.user_data.get("admin_step")

    # এডমিন প্রাইস আপডেট
    if user_id == ADMIN_TELEGRAM_ID and admin_step == "AWAITING_NEW_PRICE":
        try:
            new_price = float(text)
            coin_key = context.user_data.get("admin_coin")
            
            # ফায়ারবেসে দাম আপডেট
            db.reference(f'coin_configs/{coin_key}').update({'price': new_price})
            
            context.user_data["admin_step"] = None
            await update.message.reply_text(f"✅ দাম সফলভাবে আপডেট করা হয়েছে: `{new_price} ৳`", parse_mode="Markdown")
            return
        except ValueError:
            await update.message.reply_text("⚠️ অনুগ্রহ করে সংখ্যা লিখুন:")
            return

    if not step:
        return

    if step == "AWAITING_AMOUNT":
        try:
            amount = int(text)
            if amount < MIN_AMOUNT:
                await update.message.reply_text(f"⚠️ সর্বনিম্ন পরিমাণ {MIN_AMOUNT} কয়েন। আবার লিখুন:")
                return
            context.user_data["amount"] = amount
            coin_key = context.user_data["selected_coin"]

            if "topfollow" in coin_key:
                context.user_data["step"] = "AWAITING_COUPON"
                await update.message.reply_text("ধাপ ২: আপনার **Coupon Code** টি লিখুন:")
            else:
                context.user_data["step"] = "AWAITING_SENDER"
                await update.message.reply_text("ধাপ ২: ইউজারনেম/আইডি লিখুন:")
        except ValueError:
            await update.message.reply_text("⚠️ অনুগ্রহ করে সংখ্যা লিখুন:")

    elif step in ["AWAITING_SENDER", "AWAITING_COUPON"]:
        context.user_data["sender_info"] = text
        context.user_data["step"] = "AWAITING_NAGAD"
        await update.message.reply_text("ধাপ ৩: পেমেন্টের জন্য **নগদ (Nagad)** নম্বর দিন:")

    elif step == "AWAITING_NAGAD":
        nagad_number = text
        coin_key = context.user_data["selected_coin"]
        coins_data = db.reference('coin_configs').get() or DEFAULT_COINS
        coin = coins_data[coin_key]
        amount = context.user_data["amount"]
        sender_info = context.user_data["sender_info"]

        amount_k = amount / 1000
        gross_taka = amount_k * coin["price"]
        net_taka = max(0, gross_taka - DEFAULT_FEE)

        context.user_data["step"] = None

        req_ref = db.reference('requests').push()
        req_id = req_ref.key
        
        req_data = {
            "req_id": req_id,
            "user_id": user_id,
            "user_name": update.effective_user.first_name,
            "username": update.effective_user.username or "N/A",
            "coin_label": coin["label"],
            "amount": amount,
            "sender_info": sender_info,
            "nagad_number": nagad_number,
            "net_taka": net_taka,
            "status": "Pending",
            "timestamp": int(time.time())
        }
        
        # ফায়ারবেসে রিকোয়েস্ট স্থায়ীভাবে সেভ
        req_ref.set(req_data)

        await update.message.reply_text(
            "⏳ **আপনার রিকোয়েস্টটি সাবমিট হয়েছে!**\nএডমিন ভেরিফাই করে পেমেন্ট পাঠিয়ে দেবে।",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )

        admin_notice = (
            "🚨 **নতুন কয়েন সেল রিকোয়েস্ট (Saved to DB)!**\n\n"
            f"👤 **ইউজার:** {update.effective_user.first_name} (@{update.effective_user.username or 'N/A'})\n"
            f"🆔 **UID:** `{user_id}`\n"
            f"🪙 **কয়েন:** {coin['label']}\n"
            f"📦 **পরিমাণ:** {amount_k}K ({amount})\n"
            f"📩 **প্রেরক/কুপন:** `{sender_info}`\n"
            f"📱 **নগদ:** `{nagad_number}`\n"
            f"💰 **পেমেন্ট:** `{net_taka} ৳`\n"
        )

        admin_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Accept & Pay", callback_data=f"admin_accept_{req_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_{req_id}"),
            ]
        ])

        await context.bot.send_message(chat_id=ADMIN_TELEGRAM_ID, text=admin_notice, reply_markup=admin_keyboard, parse_mode="Markdown")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_TELEGRAM_ID:
        return

    coins_data = db.reference('coin_configs').get() or DEFAULT_COINS
    admin_text = "⚙️ **Admin Panel**\nকয়েনের দাম পরিবর্তন করতে বেছে নিন:"
    keyboard = []
    for key, coin in coins_data.items():
        keyboard.append([InlineKeyboardButton(f"✏️ {coin['label']} ({coin['price']}৳)", callback_data=f"change_price_{key}")])

    await update.message.reply_text(admin_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- ৭. প্রধান প্রসেস শুরু ---
def main():
    # Flask Server & Keep-Alive চালু করার থ্রেড
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))

    print("Earning Elevated 24/7 Firebase Bot Started...")
    app.run_polling()

if __name__ == "__main__":
    main()
    
