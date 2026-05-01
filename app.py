from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

DATABASE_URL = os.getenv('DATABASE_URL')

def get_db_connection():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL is not set. Please check your .env file.")
    return psycopg2.connect(DATABASE_URL)

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

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/admin')
def admin():
    return send_from_directory('.', 'admin.html')

@app.route('/api/checkout', methods=['POST'])
def checkout():
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    name = data.get('name')
    phone = data.get('phone')
    address = data.get('address')
    total_price = data.get('totalPrice')
    payment_method = data.get('paymentMethod')
    items = data.get('items')
    
    if not all([name, phone, address, total_price, payment_method, items]):
        return jsonify({'error': 'Missing required fields'}), 400

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
        return jsonify({'success': True, 'message': 'Order placed successfully!', 'orderId': order_id}), 201
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
        c = conn.cursor(cursor_factory=RealDictCursor)
        
        c.execute('SELECT * FROM orders ORDER BY created_at DESC')
        orders = c.fetchall()
        
        c.execute('SELECT * FROM contacts ORDER BY created_at DESC')
        contacts = c.fetchall()
        
        conn.close()
        return jsonify({'success': True, 'orders': orders, 'contacts': contacts})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Make sure to run init_db to set up the tables
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
