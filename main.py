from flask import Flask, request, jsonify
import os
import zipfile
import pandas as pd
import PyPDF2
from werkzeug.utils import secure_filename
import json
from file_handler import process_uploaded_file
from question_handler import process_question

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello, Checking Vercel!"





@app.route('/api/', methods=['POST'])
def answer_question():
    question = request.form.get('question')
    file = request.files.get('file')
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    extracted_data = process_uploaded_file(file) if file else None
    answer = process_question(question, extracted_data)
    
    return jsonify({'answer': str(answer)})

if __name__ == '__main__':
    app.run(debug=True)


