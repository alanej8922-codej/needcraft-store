from flask import Flask, jsonify
import sys

app = Flask(__name__)

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def catch_all(path):
    return jsonify({
        "status": "success",
        "message": "Hello from Vercel Python!",
        "python_version": sys.version
    })
