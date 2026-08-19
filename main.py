import logging
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

import config
import database
import server

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🛒 Sell Coins", callback_data="menu_sell"), InlineKeyboardButton("📊 Live Rates", callback_data="menu_rates")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="menu_leaderboard"), InlineKeyboardButton("📜 My History", callback_data="menu_history")],
        [InlineKeyboardButton("🌐 Open Full Web App", web_app=WebAppInfo(url=config.WEB_APP_URL))],
        [InlineKeyboardButton("📢 Official Channel", url="https://t.me/EducationPointBD"), InlineKeyboardButton("👨‍💻 Support", url="https://t.me/educationpointbd24")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    database.init_db()
    
    welcome_text = f"👋 **Earning Elevated**-এ আপনাকে স্বাগতম, {user.first_name}!\n\nনিচের বাটনগুলো ব্যবহার করে লেনদেন শুরু করুন:"
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    coins = database.get_coins()

    if data == "main_menu":
        await start(update, context)

    elif data == "menu_rates":
        text = "📊 **Live Market Rates (প্রতি ১০০০ কয়েন):**\n\n"
        for k, v in coins.items():
            status = "✅ Active" if v.get("active", True) else "❌ Stop"
            text += f"• **{v['label']}**: {v['price']} ৳ ({status})\n"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]), parse_mode="Markdown")

    elif data == "menu_sell":
        btn = [[InlineKeyboardButton(f"Sell {v['label']} ({v['price']}৳)", callback_data=f"sell_{k}")] for k, v in coins.items() if v.get("active", True)]
        btn.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
        await query.edit_message_text("🛒 **কোন কয়েনটি বিক্রি করতে চান বেছে নিন:**", reply_markup=InlineKeyboardMarkup(btn), parse_mode="Markdown")

    elif data.startswith("sell_"):
        coin_key = data.split("_")[1]
        coin = coins.get(coin_key)
        context.user_data["selected_coin"] = coin_key
        context.user_data["step"] = "AWAITING_AMOUNT"

        target = coin['target']
        inst = f"👉 কুপন এডমিনকে দিন: `{target}`" if "topfollow" in coin_key else f"👉 এই আইডিতে কয়েন পাঠান: `{target}`"
        
        msg = f"✅ **{coin['label']}**\n💰 রেট: {coin['price']}৳ | ফি: {config.DEFAULT_FEE}৳\n\n{inst}\n\nধাপ ১: কয়েনের পরিমাণ লিখুন (Min 50000):"
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="menu_sell")]]), parse_mode="Markdown")

    elif data.startswith("admin_accept_") or data.startswith("admin_reject_"):
        if user_id != config.ADMIN_TELEGRAM_ID:
            return
        
        action, req_id = data.rsplit("_", 1)
        req = database.get_request(req_id)
        if not req or req.get("status") != "Pending":
            await query.edit_message_text(query.message.text + "\n\n⚠️ **ইতিমধ্যে প্রসেস করা হয়েছে।**")
            return

        if action == "admin_accept":
            database.update_request_status(req_id, "Accepted")
            await context.bot.send_message(req["user_id"], f"✅ **আপনার সেল রিকোয়েস্ট একসেপ্ট হয়েছে!**\n💰 টাকা: {req['net_taka']}৳ নগদ পেমেন্ট করা হয়েছে।", parse_mode="Markdown")
            await query.edit_message_text(query.message.text + "\n\n✅ **ACCEPTED and User Notified!**")
        else:
            database.update_request_status(req_id, "Rejected")
            await context.bot.send_message(req["user_id"], "❌ **আপনার সেল রিকোয়েস্টটি বাতিল করা হয়েছে।**", parse_mode="Markdown")
            await query.edit_message_text(query.message.text + "\n\n❌ **REJECTED!**")

    elif data.startswith("change_price_"):
        if user_id != config.ADMIN_TELEGRAM_ID: return
        coin_key = data.split("_")[2]
        context.user_data["admin_step"] = "AWAITING_NEW_PRICE"
        context.user_data["admin_coin"] = coin_key
        await query.edit_message_text(f"✏️ **{coins[coin_key]['label']}**-এর নতুন দাম লিখুন:")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    step = context.user_data.get("step")
    admin_step = context.user_data.get("admin_step")

    if user_id == config.ADMIN_TELEGRAM_ID and admin_step == "AWAITING_NEW_PRICE":
        try:
            price = float(text)
            database.update_coin_price(context.user_data["admin_coin"], price)
            context.user_data["admin_step"] = None
            await update.message.reply_text(f"✅ নতুন দাম আপডেট হয়েছে: `{price} ৳`", parse_mode="Markdown")
            return
        except ValueError:
            await update.message.reply_text("⚠️ সঠিক সংখ্যা লিখুন:")
            return

    if not step: return

    if step == "AWAITING_AMOUNT":
        try:
            amt = int(text)
            if amt < config.MIN_AMOUNT:
                await update.message.reply_text("⚠️ সর্বনিম্ন ৫০,০০০ কয়েন দিতে হবে।")
                return
            context.user_data["amount"] = amt
            coin_key = context.user_data["selected_coin"]
            context.user_data["step"] = "AWAITING_COUPON" if "topfollow" in coin_key else "AWAITING_SENDER"
            label = "Coupon Code" if "topfollow" in coin_key else "Sender Username/ID"
            await update.message.reply_text(f"ধাপ ২: আপনার **{label}** দিন:")
        except ValueError:
            await update.message.reply_text("⚠️ সংখ্যা লিখুন:")

    elif step in ["AWAITING_SENDER", "AWAITING_COUPON"]:
        context.user_data["sender_info"] = text
        context.user_data["step"] = "AWAITING_NAGAD"
        await update.message.reply_text("ধাপ ৩: আপনার **নগদ (Nagad)** নম্বর দিন:")

    elif step == "AWAITING_NAGAD":
        nagad = text
        coin_key = context.user_data["selected_coin"]
        coin = database.get_coins()[coin_key]
        amt = context.user_data["amount"]
        sender = context.user_data["sender_info"]
        
        net_taka = max(0, (amt / 1000) * coin["price"] - config.DEFAULT_FEE)
        context.user_data["step"] = None

        req_id = database.save_request({
            "user_id": user_id, "user_name": update.effective_user.first_name,
            "username": update.effective_user.username or "N/A", "coin_label": coin["label"],
            "amount": amt, "sender_info": sender, "nagad_number": nagad,
            "net_taka": net_taka, "status": "Pending", "timestamp": int(time.time())
        })

        await update.message.reply_text("⏳ **রিকোয়েস্ট সাবমিট হয়েছে!** এডমিন ভেরিফাই করে পেমেন্ট পাঠিয়ে দেবে।", reply_markup=get_main_keyboard(), parse_mode="Markdown")

        admin_msg = f"🚨 **নতুন সেল রিকোয়েস্ট!**\n\n👤 ইউজার: {update.effective_user.first_name} (@{update.effective_user.username})\n🆔 UID: `{user_id}`\n🪙 কয়েন: {coin['label']}\n📦 পরিমাণ: {amt}\n📩 কুপন/আইডি: `{sender}`\n📱 নগদ: `{nagad}`\n💰 পেমেন্ট: `{net_taka} ৳`"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Accept", callback_data=f"admin_accept_{req_id}"), InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_{req_id}")]])
        await context.bot.send_message(config.ADMIN_TELEGRAM_ID, admin_msg, reply_markup=kb, parse_mode="Markdown")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_TELEGRAM_ID: return
    coins = database.get_coins()
    btn = [[InlineKeyboardButton(f"✏️ {v['label']} ({v['price']}৳)", callback_data=f"change_price_{k}")] for k, v in coins.items()]
    await update.message.reply_text("⚙️ **Admin Panel**\nদাম পরিবর্তন করতে সিলেক্ট করুন:", reply_markup=InlineKeyboardMarkup(btn), parse_mode="Markdown")

def main():
    database.init_db()
    server.start_server()
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("Engine Started 24/7...")
    app.run_polling()

if __name__ == "__main__":
    main()
