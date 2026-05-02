from flask import Flask, request, jsonify
from flask_cors import CORS
import razorpay
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET')
DATABASE_URL = os.getenv('DATABASE_URL')

def get_db_connection():
    if not DATABASE_URL:
        return None
    try:
        # psycopg2 handles the URL directly!
        return psycopg2.connect(DATABASE_URL, sslmode='require')
    except Exception as e:
        print(f"DB Connection Error: {e}")
        return None

@app.route('/api/hello')
def hello():
    return "Needcraft API is officially LIVE with psycopg2!"

@app.route('/api/products', methods=['GET'])
def get_products():
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Database connection failed'}), 500
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM products ORDER BY created_at ASC')
        products = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify({'success': True, 'products': products})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/create-order', methods=['POST'])
def create_order():
    try:
        data = request.json
        amount = data.get('amount')
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        order = client.order.create({
            'amount': int(amount),
            'currency': 'INR',
            'payment_capture': '1'
        })
        return jsonify(order)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/verify-payment', methods=['POST'])
def verify_payment():
    try:
        data = request.json
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        params_dict = {
            'razorpay_order_id': data.get('razorpay_order_id'),
            'razorpay_payment_id': data.get('razorpay_payment_id'),
            'razorpay_signature': data.get('razorpay_signature')
        }
        client.utility.verify_payment_signature(params_dict)
        
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute(
                'INSERT INTO orders (name, phone, address, total_price, items, payment_method, razorpay_order_id, razorpay_payment_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                (data.get('name'), data.get('phone'), data.get('address'), data.get('totalPrice'), data.get('items'), data.get('paymentMethod'), data.get('razorpay_order_id'), data.get('razorpay_payment_id'))
            )
            conn.commit()
            cur.close()
            conn.close()
            return jsonify({'success': True})
        return jsonify({'error': 'DB error'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/contact', methods=['POST'])
def contact():
    try:
        data = request.json
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('INSERT INTO contacts (name, email, message) VALUES (%s, %s, %s)', (data.get('name'), data.get('email'), data.get('message')))
            conn.commit()
            cur.close()
            conn.close()
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/data', methods=['GET'])
def admin_data():
    conn = get_db_connection()
    if not conn: return jsonify({'error': 'DB error'}), 500
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM orders ORDER BY created_at DESC')
        orders = cur.fetchall()
        cur.execute('SELECT * FROM contacts ORDER BY created_at DESC')
        contacts = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify({'success': True, 'orders': orders, 'contacts': contacts})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
