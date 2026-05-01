from flask import Flask, request, jsonify
import razorpay
import os

# We don't need a full Flask app for a single function, but Vercel supports it.
# However, a simpler way is to just define a 'handler' or use Flask.
app = Flask(__name__)

RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET')

@app.route('/api/create-order', methods=['POST'])
def handler():
    try:
        data = request.json
        amount = data.get('amount')
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        order = client.order.create({'amount': int(amount), 'currency': 'INR', 'payment_capture': '1'})
        return jsonify(order)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
