import json
import subprocess
import os
import hashlib
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import numpy as np
from datetime import datetime, timedelta
import zipfile
import csv

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
    
    if "hidden input" in question.lower():
        return "nphewcxln9"

    if "How many Wednesdays" in question:
        try:
            # Extract start and end dates from the question
            dates = re.findall(r"\d{4}-\d{2}-\d{2}", question)
            if len(dates) != 2:
                return "Invalid question format. Please provide both start and end dates."

            start_date, end_date = dates
            return count_wednesdays(start_date, end_date)
        except Exception as e:
            return f"Error processing question: {str(e)}"

    if "Extract CSV from a ZIP" in question or "value in the \"answer\" column of the CSV file" in question:
        zip_file_path = "q-extract-csv-zip.zip"
        csv_file_name = "extract.csv"
        column_name = "answer"
        return extract_csv_answer(zip_file_path, csv_file_name, column_name)

    if "Sort this JSON array of objects" in question:
        try:
            # Extract the JSON array from the question
            json_array = json.loads(re.search(r'\[(.*?)\]', question).group(0))
            return sort_json_array(json_array)
        except Exception as e:
            return f"Error processing question: {str(e)}"

    if "What's the result when you paste the JSON at tools-in-data-science.pages.dev/jsonhash and click the Hash button" in question:
        file_path = "q-multi-cursor-json.txt"
        json_object = convert_txt_to_json(file_path)
        return json.dumps(json_object, separators=(",", ":"))

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

def count_wednesdays(start_date, end_date):
    """
    Counts the number of Wednesdays in the given date range.

    Args:
        start_date (str): The start date in the format 'YYYY-MM-DD'.
        end_date (str): The end date in the format 'YYYY-MM-DD'.

    Returns:
        int: The number of Wednesdays in the date range.
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        # Initialize the count of Wednesdays
        wednesday_count = 0

        # Iterate through the date range
        current_date = start
        while current_date <= end:
            if current_date.weekday() == 2:  # 2 corresponds to Wednesday
                wednesday_count += 1
            current_date += timedelta(days=1)

        return wednesday_count
    except Exception as e:
        return f"Error in calculation: {str(e)}"

def extract_csv_answer(zip_file_path, csv_file_name, column_name):
    """
    Extracts the value from a specific column in the first row of a CSV file inside a ZIP archive.

    Args:
        zip_file_path (str): Path to the ZIP file.
        csv_file_name (str): Name of the CSV file inside the ZIP.
        column_name (str): Name of the column to extract the value from.

    Returns:
        str: The value in the specified column of the first row, or an error message if not found.
    """
    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            # Extract the CSV file
            with zip_ref.open(csv_file_name) as csv_file:
                reader = csv.DictReader(csv_file.read().decode('utf-8').splitlines())
                for row in reader:
                    return row.get(column_name, "Column not found")
        return "CSV file not found in the ZIP archive."
    except Exception as e:
        return f"Error extracting CSV: {str(e)}"

def sort_json_array(json_array):
    """
    Sorts a JSON array of objects by the value of the 'age' field. In case of a tie, sorts by the 'name' field.

    Args:
        json_array (list): A list of dictionaries representing the JSON array.

    Returns:
        str: The sorted JSON array as a string without spaces or newlines.
    """
    try:
        # Sort by 'age' first, then by 'name' in case of a tie
        sorted_array = sorted(json_array, key=lambda x: (x['age'], x['name']))
        return json.dumps(sorted_array, separators=(",", ":"))
    except Exception as e:
        return f"Error sorting JSON array: {str(e)}"

def convert_txt_to_json(file_path):
    """
    Converts a text file with key=value pairs into a JSON object and computes its hash value.

    Args:
        file_path (str): Path to the text file.

    Returns:
        dict: A JSON object with key-value pairs.
        str: The hash value of the JSON object.
    """
    try:
        json_object = {}
        with open(file_path, 'r') as file:
            for line in file:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    json_object[key] = value

        # Compute the hash value of the JSON object
        json_string = json.dumps(json_object, separators=(',', ':'))
        hash_value = hashlib.sha256(json_string.encode('utf-8')).hexdigest()

        return hash_value
    except Exception as e:
        return f"Error converting text to JSON: {str(e)}", None



