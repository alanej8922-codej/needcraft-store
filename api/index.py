from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import pg8000.dbapi
import urllib.parse
import razorpay

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.getenv('DATABASE_URL')
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET')

def get_db_connection():
    if not DATABASE_URL:
        return None
    url = urllib.parse.urlparse(DATABASE_URL)
    return pg8000.dbapi.connect(
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port,
        database=url.path[1:]
    )

@app.route('/api/create-order', methods=['POST'])
def create_order():
    try:
        data = request.json
        amount = data.get('amount')
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        order = client.order.create({'amount': int(amount), 'currency': 'INR', 'payment_capture': '1'})
        return jsonify(order)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/verify-payment', methods=['POST'])
def verify_payment():
    try:
        data = request.json
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        client.utility.verify_payment_signature(data)
        
        conn = get_db_connection()
        if conn:
            c = conn.cursor()
            c.execute('INSERT INTO orders (name, phone, address, total_price, items) VALUES (%s, %s, %s, %s, %s)', 
                     (data.get('name'), data.get('phone'), data.get('address'), data.get('totalPrice'), data.get('items')))
            conn.commit()
            conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/hello')
def hello():
    return jsonify({"message": "Python is working!"})

