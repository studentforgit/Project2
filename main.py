from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import logging
from file_handler import process_uploaded_file
from question_handler import process_question

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
CORS(app)

@app.route("/", methods=["GET", "POST"])
def index():
    return "Hello, World!"

@app.route('/api/', methods=['POST', 'OPTIONS'])
def answer_question():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    question = request.form.get('question')
    file = request.files.get('file')
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    extracted_data = process_uploaded_file(file) if file else None
    answer = process_question(question, extracted_data)
    
    return _corsify_actual_response(jsonify({'answer': str(answer)}))

# Helper functions to handle CORS responses
def _build_cors_preflight_response():
    response = jsonify({})
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
    return response

def _corsify_actual_response(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

# Allow running locally with Flask
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)  # Local execution

# Directly expose the Flask app as `app` for Vercel
