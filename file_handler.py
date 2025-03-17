import os
import zipfile
import pandas as pd
import PyPDF2
from werkzeug.utils import secure_filename

def extract_text_from_pdf(pdf_path):
    text = ""
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text.strip()

def process_uploaded_file(file):
    if not file:
        return None
    
    filename = secure_filename(file.filename)
    file_ext = os.path.splitext(filename)[1].lower()
    extracted_data = None
    
    if file_ext == ".zip":
        file.save(filename)
        with zipfile.ZipFile(filename, 'r') as zip_ref:
            zip_ref.extractall("extracted")
        os.remove(filename)
        
        csv_files = [f for f in os.listdir("extracted") if f.endswith(".csv")]
        if csv_files:
            df = pd.read_csv(os.path.join("extracted", csv_files[0]))
            extracted_data = df.to_dict()
        
    elif file_ext == ".csv":
        df = pd.read_csv(file)
        extracted_data = df.to_dict()
        
    elif file_ext == ".xlsx":
        df = pd.read_excel(file)
        extracted_data = df.to_dict()
        
    elif file_ext == ".pdf":
        file.save(filename)
        extracted_data = extract_text_from_pdf(filename)
        os.remove(filename)
        
    elif file_ext == ".txt":
        extracted_data = file.read().decode("utf-8")
    
    return extracted_data
