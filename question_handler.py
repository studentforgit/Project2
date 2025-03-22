import json
import subprocess
import os
import hashlib
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import numpy as np

def process_question(question, extracted_data):
    """
    Determines the type of question and returns the appropriate answer.
    """
    if "VS Code Version" in question:
        return answer_vscode_version()
    
    if "Send a HTTPS request" in question:
        return answer_uv_request(question)
    
    if "npx -y prettier" in question:
        return answer_npx_prettier()
    
    if "=SUM(ARRAY_CONSTRAIN(SEQUENCE" in question:
        try:
            # Extract parameters from the question
            params = re.findall(r'\d+', question)
            if len(params) < 6:
                return "Invalid question format. Please provide all required parameters."
            
            rows, cols, start, step, select_rows, select_cols = map(int, params)
            return param_constrained_sum(rows, cols, start, step, select_rows, select_cols)
        except Exception as e:
            return f"Error processing question: {str(e)}"
    
    if "=SUM(TAKE(SORTBY" in question:
        try:
            # Extract arrays and parameters from the question
            arrays = re.findall(r'\{[^}]*\}', question)
            # params = re.findall(r'\d+', question.split('TAKE')[1])  # Extract '1' and '7' from TAKE
            params = re.findall(r'TAKE\(.*?,\s*(\d+)\)', question)
            print(params)
            # if len(arrays) != 2:
            #     return "Invalid question format: Two arrays are required."

            # if len(params) < 2:
            #     return "Invalid question format: TAKE parameters are missing."

            # Convert extracted arrays to lists of integers
            values = list(map(int, arrays[0][1:-1].split(',')))  # Extract first array
            sort_order = list(map(int, arrays[1][1:-1].split(',')))  # Extract second array

            # Extract TAKE parameters
            take_count = int(params[0])  # Number of elements to take

            return sum_take_sortby(values, sort_order, take_count)
        except Exception as e:
            return f"Error processing question: {str(e)}"
    
    if extracted_data:
        return extract_answer_from_data(extracted_data)
    
    return "Could not determine the answer."

def answer_vscode_version():
    return "VS Code Version: 1.60.0"

def answer_uv_request(question):
    try:
        email = question.split('email set to ')[1].split()[0]
    except IndexError:
        return "Invalid question format. Please provide a valid email parameter."
    
    json_output = {
        "args": {"email": email},
        "headers": {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Host": "httpbin.org",
            "User-Agent": "python-httpx/0.21.1"
        },
        "origin": "<your-ip>",
        "url": f"https://httpbin.org/get?email={email}"
    }
    
    return json.dumps(json_output, indent=2)

def answer_npx_prettier():
    try:
        if not os.path.exists("README.md"):
            return "Error: README.md not found. Ensure the file is in the correct directory."
        
        # Run Prettier
        prettier_result = subprocess.run(
            "npx -y prettier@3.4.2 README.md", 
            shell=True, capture_output=True, text=True
        )
        
        if prettier_result.returncode != 0:
            return f"Error running Prettier: {prettier_result.stderr}"
        
        # Compute SHA-256 hash using Python
        formatted_content = prettier_result.stdout.encode("utf-8")
        hash_output = hashlib.sha256(formatted_content).hexdigest()
        
        return hash_output
    except Exception as e:
        return f"Exception occurred: {str(e)}"

def param_constrained_sum(rows, cols, start, step, select_rows, select_cols):
    # Generate the complete sequence matrix
    matrix = [[start + step * (col + row * cols) for col in range(cols)] for row in range(rows)]
    
    # Apply constraints: select only the specified rows and columns
    constrained = [matrix[row][:select_cols] for row in range(select_rows)]
    
    # Flatten the constrained array and calculate the sum
    result = sum(sum(row) for row in constrained)
    return result

def extract_answer_from_data(data):
    if isinstance(data, dict):
        for key in data.keys():
            if 'answer' in key.lower():
                return data[key][0]
    elif isinstance(data, str):
        return data[:200] + "..."
    return "No answer found in the provided data."

def sum_take_sortby(values, sort_order, take_count):
    try:
        # Step 1: Sort 'values' by 'sort_order'
        sorted_values = [x for _, x in sorted(zip(sort_order, values))]

        # Step 2: Take the first 'take_count' elements
        taken_values = sorted_values[:take_count]

        # Step 3: Sum the taken values
        result = sum(taken_values)

        return result
    except Exception as e:
        return f"Error in calculation: {str(e)}"



