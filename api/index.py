from flask import Flask, jsonify
import razorpay
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

@app.route('/api/hello')
def hello():
    return "Razorpay library loaded successfully!"

@app.route('/api/products')
def products():
    return jsonify({"success": True, "products": [], "message": "Razorpay test mode"})
