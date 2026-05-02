from flask import Flask, request, jsonify
from flask_cors import CORS
import razorpay
import os
# import pg8000
import urllib.parse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# API Routes

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
        
        return pg8000.connect(
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
                    payment_method TEXT,
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
            # Create products table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    price DECIMAL(10, 2) NOT NULL,
                    original_price DECIMAL(10, 2),
                    image_url TEXT,
                    hover_image_url TEXT,
                    badge TEXT,
                    is_best_seller BOOLEAN DEFAULT FALSE,
                    is_eco_friendly BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            print("Database tables initialized successfully")
        except Exception as e:
            print(f"Error initializing database: {str(e)}")
        finally:
            conn.close()

def seed_products():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM products')
            if cursor.fetchone()[0] == 0:
                print("Seeding initial products...")
                products = [
                    ('Thumb Wall Hooks (Pack of 10)', 'Thumb Wall Hooks for Hanging, Cable Clips, No Punching Key Hook Holder, Wall Hangers Silicone Hooks Desk Wire Management, Random Color, Pack of 10 (Big Size), Multicolour.', 200, 399, 'thumb_hook.png', 'https://images.unsplash.com/photo-1616401784845-180882ba9ba8?q=80&w=600&auto=format&fit=crop', 'Best Seller', True, False),
                    ('(5 Pc Combo) Stainless Steel Straw Set', 'Premium reusable stainless steel straw set for juices & smoothies. Includes a cleaning brush. A trending kitchen product & travel must-have!', 250, 499, 'steel_straw_set.png', 'https://images.unsplash.com/photo-1544457070-4cd773b4d71e?q=80&w=600&auto=format&fit=crop', 'Eco-Friendly', False, True)
                ]
                for p in products:
                    cursor.execute('''
                        INSERT INTO products (name, description, price, original_price, image_url, hover_image_url, badge, is_best_seller, is_eco_friendly)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', p)
                conn.commit()
                print("Products seeded successfully")
        except Exception as e:
            print(f"Error seeding products: {str(e)}")
        finally:
            conn.close()

# Routes
@app.route('/api/products', methods=['GET'])
def get_products():
    # TEMPORARILY DISABLED DB CHECK
    # try:
    #     init_db()
    #     seed_products()
    # except:
    #     pass

    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM products ORDER BY created_at ASC')
            rows = cursor.fetchall()
            products = []
            for r in rows:
                products.append({
                    'id': r[0],
                    'name': r[1],
                    'description': r[2],
                    'price': float(r[3]),
                    'original_price': float(r[4]) if r[4] else None,
                    'image_url': r[5],
                    'hover_image_url': r[6],
                    'badge': r[7],
                    'is_best_seller': r[8],
                    'is_eco_friendly': r[9]
                })
            conn.close()
            return jsonify({'success': True, 'products': products})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/products', methods=['POST'])
def add_product():
    try:
        data = request.json
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO products (name, description, price, original_price, image_url, hover_image_url, badge, is_best_seller, is_eco_friendly)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                data.get('name'),
                data.get('description'),
                data.get('price'),
                data.get('original_price'),
                data.get('image_url'),
                data.get('hover_image_url'),
                data.get('badge'),
                data.get('is_best_seller', False),
                data.get('is_eco_friendly', False)
            ))
            conn.commit()
            conn.close()
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
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
                'INSERT INTO orders (name, phone, address, total_price, items, payment_method, razorpay_order_id, razorpay_payment_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                (
                    data.get('name'),
                    data.get('phone'),
                    data.get('address'),
                    data.get('totalPrice'),
                    data.get('items'),
                    data.get('paymentMethod'),
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
                    'payment_method': row[6] or 'N/A',
                    'order_id': row[7],
                    'payment_id': row[8],
                    'created_at': row[9]
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
            return jsonify({'success': True, 'orders': orders_list, 'contacts': contacts_list})
        else:
            return jsonify({'error': 'Database connection failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# For local testing
if __name__ == '__main__':
    app.run(debug=True, port=5000)
