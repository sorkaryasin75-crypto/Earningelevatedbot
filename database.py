import firebase_admin
from firebase_admin import credentials, db
import config

def init_db():
    if not firebase_admin._apps:
        cred = credentials.Certificate("firebase-key.json")
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://sell-point-it-default-rtdb.firebaseio.com'
        })
    
    coins_ref = db.reference('coin_configs')
    if not coins_ref.get():
        coins_ref.set(config.DEFAULT_COINS)

def get_coins():
    return db.reference('coin_configs').get() or config.DEFAULT_COINS

def update_coin_price(coin_key, price):
    db.reference(f'coin_configs/{coin_key}').update({'price': price})

def save_request(req_data):
    ref = db.reference('requests').push()
    req_data['req_id'] = ref.key
    ref.set(req_data)
    return ref.key

def update_request_status(req_id, status):
    db.reference(f'requests/{req_id}').update({'status': status})

def get_request(req_id):
    return db.reference(f'requests/{req_id}').get()
