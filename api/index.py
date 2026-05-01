import traceback
try:
    from flask import Flask, request, jsonify, send_from_directory
    from flask_cors import CORS
    import pg8000.dbapi
    import urllib.parse
    import os
    from dotenv import load_dotenv
    import razorpay

    # Load environment variables from .env file
    load_dotenv()

    app = Flask(__name__, static_folder='.', static_url_path='')
    CORS(app)

    DATABASE_URL = os.getenv('DATABASE_URL')
    RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID')
    RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET')
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)) if RAZORPAY_KEY_ID else None

def get_db_connection():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL is not set.")
    url = urllib.parse.urlparse(DATABASE_URL)
    
    # URL decode password in case it contains @ or other special characters
    password = urllib.parse.unquote(url.password) if url.password else None
    
    return pg8000.dbapi.connect(
        user=url.username,
        password=password,
        host=url.hostname,
        port=url.port,
        database=url.path[1:]
    )

def init_db():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        # Create orders table
        c.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                total_price INTEGER NOT NULL,
                payment_method TEXT NOT NULL,
                items TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Create contacts table
        c.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        print("Supabase database initialized successfully!")
    except Exception as e:
        print("Database connection failed. Please check your DATABASE_URL in .env.")
        print(e)

# Static routes removed for Vercel native serving

@app.route('/api/create-order', methods=['POST'])
def create_order():
    data = request.json
    amount = data.get('amount')
    currency = data.get('currency', 'INR')
    
    if not amount or int(amount) < 100:
        return jsonify({'error': 'Invalid amount'}), 400
        
    try:
        order = razorpay_client.order.create({
            'amount': int(amount),
            'currency': currency,
            'payment_capture': '1'
        })
        return jsonify(order)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/verify-payment', methods=['POST'])
def verify_payment():
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_signature = data.get('razorpay_signature')
    
    name = data.get('name')
    phone = data.get('phone')
    address = data.get('address')
    total_price = data.get('totalPrice')
    payment_method = data.get('paymentMethod', 'Razorpay')
    items = data.get('items')
    
    if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
        return jsonify({'error': 'Missing payment verification fields'}), 400

    try:
        razorpay_client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        })
    except razorpay.errors.SignatureVerificationError:
        return jsonify({'error': 'Payment signature verification failed'}), 400

    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO orders (name, phone, address, total_price, payment_method, items)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        ''', (name, phone, address, total_price, payment_method, items))
        order_id = c.fetchone()[0]
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Payment successful and order placed!', 'orderId': order_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/contact', methods=['POST'])
def contact():
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    name = data.get('name')
    email = data.get('email')
    message = data.get('message')
    
    if not all([name, email, message]):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO contacts (name, email, message)
            VALUES (%s, %s, %s)
        ''', (name, email, message))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Message sent successfully!'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/data', methods=['GET'])
def admin_data():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute('SELECT id, name, phone, address, total_price, payment_method, items, created_at FROM orders ORDER BY created_at DESC')
        orders_raw = c.fetchall()
        orders = []
        for row in orders_raw:
            orders.append({
                'id': row[0], 'name': row[1], 'phone': row[2], 'address': row[3],
                'total_price': row[4], 'payment_method': row[5], 'items': row[6], 'created_at': row[7]
            })
        
        c.execute('SELECT id, name, email, message, created_at FROM contacts ORDER BY created_at DESC')
        contacts_raw = c.fetchall()
        contacts = []
        for row in contacts_raw:
            contacts.append({
                'id': row[0], 'name': row[1], 'email': row[2], 'message': row[3], 'created_at': row[4]
            })
            
        conn.close()
        return jsonify({'success': True, 'orders': orders, 'contacts': contacts})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

except Exception as startup_error:
    from flask import Flask, jsonify
    app = Flask(__name__)
    error_tb = traceback.format_exc()
    
    @app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
    @app.route('/<path:path>', methods=['GET', 'POST'])
    def catch_all(path):
        return jsonify({
            "error": "Vercel Python Initialization Crashed",
            "message": str(startup_error),
            "traceback": error_tb
        }), 500

if __name__ == '__main__':
    # Make sure to run init_db to set up the tables
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
