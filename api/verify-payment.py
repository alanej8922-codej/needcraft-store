from flask import Flask, request, jsonify
import razorpay
import os
import pg8000.dbapi
import urllib.parse

app = Flask(__name__)

RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET')
DATABASE_URL = os.getenv('DATABASE_URL')

def get_db_connection():
    if not DATABASE_URL: return None
    url = urllib.parse.urlparse(DATABASE_URL)
    return pg8000.dbapi.connect(user=url.username, password=url.password, host=url.hostname, port=url.port, database=url.path[1:])

@app.route('/api/verify-payment', methods=['POST'])
def handler():
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
