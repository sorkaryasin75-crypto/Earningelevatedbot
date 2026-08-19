import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "8312396498:AAF07jeC_2wJSxb1mVxfocwHEXJvCyz3DQ4")
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "6582650458"))
WEB_APP_URL = "https://economyshops.blogspot.com"
RENDER_APP_URL = os.getenv("RENDER_APP_URL", "https://earningelevatedbot.onrender.com")

DEFAULT_FEE = 5
MIN_AMOUNT = 50000

DEFAULT_COINS = {
    "niva": {"label": "Niva Coin", "price": 4.65, "target": "@sell_point_it", "active": True},
    "newtopfollow": {"label": "New Topfollow", "price": 4.20, "target": "@Send", "active": True},
    "oldtopfollow": {"label": "Old Topfollow", "price": 4.70, "target": "@topfollowsadmin", "active": True},
    "nsfollow": {"label": "NS Follow", "price": 12.0, "target": "@NsCoinAdmin", "active": True},
}
