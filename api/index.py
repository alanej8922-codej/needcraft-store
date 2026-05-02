from flask import Flask, request, jsonify
from flask_cors import CORS
import razorpay
import os
import pg8000.dbapi
import urllib.parse
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
        print("Error: DATABASE_URL not found in environment variables")
        return None
    try:
        url = urllib.parse.urlparse(DATABASE_URL)
        username = url.username
        password = urllib.parse.unquote(url.password) if url.password else None
        hostname = url.hostname
        port = url.port or 5432
        database = url.path[1:]
        
        print(f"Connecting to {hostname}:{port}/{database} as {username}...")
        
        return pg8000.dbapi.connect(
            user=username,
            password=password,
            host=hostname,
            port=port,
            database=database,
            ssl_context=True
        )
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        return None

def init_db():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            # Create orders table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    name TEXT,
                    phone TEXT,
                    address TEXT,
                    total_price TEXT,
                    items TEXT,
                    razorpay_order_id TEXT,
                    razorpay_payment_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Create contacts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS contacts (
                    id SERIAL PRIMARY KEY,
                    name TEXT,
                    email TEXT,
                    message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            print("Database tables initialized successfully")
        except Exception as e:
            print(f"Error initializing database: {str(e)}")
        finally:
            conn.close()

# Initialize DB on startup (in serverless environment, this runs once per cold start)
init_db()

@app.route('/api/hello', methods=['GET'])
def hello():
    return jsonify({"message": "Needcraft API is live!"})

@app.route('/api/create-order', methods=['POST'])
def create_order():
    try:
        data = request.json
        amount = data.get('amount')
        if not amount:
            return jsonify({'error': 'Amount is required'}), 400
            
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
        
        # Verify signature
        params_dict = {
            'razorpay_order_id': data.get('razorpay_order_id'),
            'razorpay_payment_id': data.get('razorpay_payment_id'),
            'razorpay_signature': data.get('razorpay_signature')
        }
        client.utility.verify_payment_signature(params_dict)
        
        # Save to database
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO orders (name, phone, address, total_price, items, razorpay_order_id, razorpay_payment_id) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                (
                    data.get('name'),
                    data.get('phone'),
                    data.get('address'),
                    data.get('totalPrice'),
                    data.get('items'),
                    data.get('razorpay_order_id'),
                    data.get('razorpay_payment_id')
                )
            )
            conn.commit()
            conn.close()
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Database connection failed'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/contact', methods=['POST'])
def contact():
    try:
        data = request.json
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO contacts (name, email, message) VALUES (%s, %s, %s)',
                (data.get('name'), data.get('email'), data.get('message'))
            )
            conn.commit()
            conn.close()
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Database connection failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/data', methods=['GET'])
def admin_data():
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            
            # Fetch orders
            cursor.execute('SELECT * FROM orders ORDER BY created_at DESC')
            orders = cursor.fetchall()
            orders_list = []
            for row in orders:
                orders_list.append({
                    'id': row[0],
                    'name': row[1],
                    'phone': row[2],
                    'address': row[3],
                    'totalPrice': row[4],
                    'items': row[5],
                    'order_id': row[6],
                    'payment_id': row[7],
                    'created_at': row[8]
                })
                
            # Fetch contacts
            cursor.execute('SELECT * FROM contacts ORDER BY created_at DESC')
            contacts = cursor.fetchall()
            contacts_list = []
            for row in contacts:
                contacts_list.append({
                    'id': row[0],
                    'name': row[1],
                    'email': row[2],
                    'message': row[3],
                    'created_at': row[4]
                })
                
            conn.close()
            return jsonify({'orders': orders_list, 'contacts': contacts_list})
        else:
            return jsonify({'error': 'Database connection failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# For local testing
if __name__ == '__main__':
    app.run(debug=True, port=5000)
