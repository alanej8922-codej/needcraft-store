from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/products')
def products():
    return jsonify({"success": True, "products": [], "message": "Debug mode: App is live!"})

@app.route('/api/hello')
def hello():
    return "API is working!"
