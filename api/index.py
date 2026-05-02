from flask import Flask, request, jsonify
from flask_cors import CORS
import razorpay
import os
import pg8000
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
        return None
    try:
        url = urllib.parse.urlparse(DATABASE_URL)
        return pg8000.connect(
            user=url.username,
            password=urllib.parse.unquote(url.password) if url.password else None,
            host=url.hostname,
            port=url.port or 5432,
            database=url.path[1:],
            ssl_context=True
        )
    except:
        return None

@app.route('/api/hello')
def hello():
    return "API is working with all libraries loaded!"

@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products ORDER BY created_at ASC')
        rows = cursor.fetchall()
        products = []
        for r in rows:
            products.append({
                'id': r[0], 'name': r[1], 'description': r[2],
                'price': float(r[3]), 'original_price': float(r[4]) if r[4] else None,
                'image_url': r[5], 'hover_image_url': r[6], 'badge': r[7]
            })
        conn.close()
        return jsonify({'success': True, 'products': products})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
