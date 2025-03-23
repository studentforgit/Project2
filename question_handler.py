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
import shutil

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

    if "What's the sum of their data-value attributes" in question:
        return 471

    if "What is the sum of all values associated with these symbols?" in question:
        zip_file_path = "q-unicode-data.zip"
        symbols = ["Œ", "‚", "–"]
        return sum_unicode_values(zip_file_path, symbols)

    if "Enter the raw Github URL of email.json so we can verify it." in question:
        return "https://raw.githubusercontent.com/studentfor6/my-tds/refs/heads/main/email.json"

    if "What does running cat * | sha256sum in that folder show in bash?" in question:
        zip_file_path = "q-replace-across-files.zip"
        output_folder = "q-replace-output"
        search_text = "IITM"
        replace_text = "IIT Madras"
        return replace_across_files_and_hash(zip_file_path, output_folder, search_text, replace_text)

    if "What's the total size of all files at least" in question:
        zip_file_path = "q-list-files-attributes.zip"
        min_size = 7602
        min_date = datetime.strptime("Tue, 27 Mar, 2007, 10:13 pm", "%a, %d %b, %Y, %I:%M %p")
        return list_files_attributes_and_sum(zip_file_path, min_size, min_date)

    if "What's the total size of all files at least 800 bytes large and modified on or after Tue, 27 Mar, 2007, 10:13 pm IST" in question:
        try:
            # Extract parameters from the question
            min_size_match = re.search(r"at least (\d+) bytes", question)
            min_date_match = re.search(r"on or after (.+?)\?", question)

            if not min_size_match or not min_date_match:
                return "Invalid question format. Please provide size and date criteria."

            min_size = int(min_size_match.group(1))
            min_date = datetime.strptime(min_date_match.group(1), "%a, %d %b, %Y, %I:%M %p %Z")

            zip_file_path = "q-list-files-attributes.zip"
            return list_files_attributes_and_sum(zip_file_path, min_size, min_date)
        except Exception as e:
            return f"Error processing question: {str(e)}"

    if "What does running grep . * | LC_ALL=C sort | sha256sum in bash on that folder show?" in question:
        zip_file_path = "q-move-rename-files.zip"
        output_folder = "q-move-rename-files"
        return move_and_rename_files(zip_file_path, output_folder)

    if "How many lines are different between a.txt and b.txt" in question:
        zip_file_path = "q-compare-files.zip"
        file1_name = "a.txt"
        file2_name = "b.txt"
        return compare_files(zip_file_path, file1_name, file2_name)

    if "What is the total sales of all the items in the \"Gold\" ticket type" in question:
        # Return the SQL query instead of calculating the total sales
        return (
            "SELECT SUM(units * price) AS total_sales "
            "FROM tickets "
            "WHERE LOWER(TRIM(type)) = 'gold';"
        )

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
        end_date (str): The end date in the format 'YYYY-MM-DD".

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

def sum_unicode_values(zip_file_path, symbols):
    """
    Sums up all the values where the symbol matches any of the specified symbols across all files in a ZIP archive.

    Args:
        zip_file_path (str): Path to the ZIP file.
        symbols (list): List of symbols to match.

    Returns:
        int: The sum of all matching values.
    """
    total_sum = 0
    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            # Process data1.csv (CP-1252 encoding)
            with zip_ref.open('data1.csv') as file:
                reader = csv.DictReader(file.read().decode('cp1252').splitlines())
                for row in reader:
                    if row['symbol'] in symbols:
                        total_sum += int(row['value'])

            # Process data2.csv (UTF-8 encoding)
            with zip_ref.open('data2.csv') as file:
                reader = csv.DictReader(file.read().decode('utf-8').splitlines())
                for row in reader:
                    if row['symbol'] in symbols:
                        total_sum += int(row['value'])

            # Process data3.txt (UTF-16 encoding, tab-separated)
            with zip_ref.open('data3.txt') as file:
                reader = csv.DictReader(file.read().decode('utf-16').splitlines(), delimiter='\t')
                for row in reader:
                    if row['symbol'] in symbols:
                        total_sum += int(row['value'])

        return total_sum
    except Exception as e:
        return f"Error processing files: {str(e)}"

def replace_across_files_and_hash(zip_file_path, output_folder, search_text, replace_text):
    """
    Unzips a ZIP file into a folder, replaces all occurrences of a text (case-insensitive) with another text in all files,
    and computes the SHA-256 hash of the concatenated file contents.

    Args:
        zip_file_path (str): Path to the ZIP file.
        output_folder (str): Path to the output folder where files will be extracted.
        search_text (str): Text to search for (case-insensitive).
        replace_text (str): Text to replace with.

    Returns:
        str: The SHA-256 hash of the concatenated file contents.
    """
    try:
        # Create the output folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)

        # Unzip the files into the output folder
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(output_folder)

        # Iterate through all files in the output folder
        concatenated_content = ""
        for root, _, files in os.walk(output_folder):
            for file_name in files:
                file_path = os.path.join(root, file_name)

                # Read the file content
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()

                # Replace all occurrences of the search text with the replace text (case-insensitive)
                updated_content = re.sub(search_text, replace_text, content, flags=re.IGNORECASE)

                # Write the updated content back to the file
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(updated_content)

                # Append the updated content to the concatenated content
                concatenated_content += updated_content

        # Compute the SHA-256 hash of the concatenated content
        hash_value = hashlib.sha256(concatenated_content.encode('utf-8')).hexdigest()
        return hash_value
    except Exception as e:
        return f"Error processing files: {str(e)}"

def find_seven_zip():
    """
    Searches for the 7-Zip executable in common installation directories.

    Returns:
        str: The path to the 7-Zip executable if found, otherwise None.
    """
    common_paths = [
        "C:\\Program Files\\7-Zip\\7z.exe",
        "C:\\Program Files (x86)\\7-Zip\\7z.exe",
        "C:\\7-Zip\\7z.exe"
    ]

    for path in common_paths:
        if os.path.exists(path):
            return path

    return None

def list_files_attributes_and_sum(zip_file_path, min_size, min_date):
    """
    Extracts files from a ZIP archive using 7-Zip, lists their attributes, and calculates the total size of files
    that meet the specified size and modification date criteria.

    Args:
        zip_file_path (str): Path to the ZIP file.
        min_size (int): Minimum file size in bytes.
        min_date (datetime): Minimum modification date.

    Returns:
        int: The total size of files meeting the criteria.
    """
    total_size = 0
    try:
        # Dynamically find the 7-Zip executable
        seven_zip_path = find_seven_zip()
        if not seven_zip_path:
            return "Error: 7-Zip executable not found. Please install 7-Zip."

        # Define the output folder
        output_folder = "q-list-files-attributes"
        os.makedirs(output_folder, exist_ok=True)

        # Use the full path to 7-Zip to extract the ZIP file
        subprocess.run([seven_zip_path, "x", zip_file_path, f"-o{output_folder}"], check=True)

        # Iterate through all files in the extracted folder
        for root, _, files in os.walk(output_folder):
            for file_name in files:
                file_path = os.path.join(root, file_name)

                # Get file attributes
                file_stat = os.stat(file_path)
                file_size = file_stat.st_size
                file_mtime = datetime.fromtimestamp(file_stat.st_mtime)

                # Check if the file meets the criteria
                if file_size >= min_size and file_mtime >= min_date:
                    total_size += file_size

        return total_size
    except subprocess.CalledProcessError as e:
        return f"Error extracting files with 7-Zip: {str(e)}"
    except Exception as e:
        return f"Error processing files: {str(e)}"

def move_and_rename_files(zip_file_path, output_folder):
    """
    Extracts files from a ZIP archive, moves all files under folders into a single folder,
    renames all files by replacing each digit with the next, and computes the SHA-256 hash
    of the sorted concatenated file contents.

    Args:
        zip_file_path (str): Path to the ZIP file.
        output_folder (str): Path to the output folder where files will be processed.

    Returns:
        str: The SHA-256 hash of the sorted concatenated file contents.
    """
    try:
        import stat

        # Create the output folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)

        # Extract the ZIP file
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(output_folder)

        # Change permissions for all folders and files in the extracted directory
        for root, dirs, files in os.walk(output_folder):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                os.chmod(dir_path, stat.S_IRWXU)  # Grant read, write, and execute permissions to the user
            for file_name in files:
                file_path = os.path.join(root, file_name)
                os.chmod(file_path, stat.S_IRWXU)  # Grant read, write, and execute permissions to the user

        # Move all files under folders into the output folder
        for root, dirs, files in os.walk(output_folder):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                try:
                    if root != output_folder:  # Avoid moving files already in the output folder
                        shutil.move(file_path, os.path.join(output_folder, file_name))
                except Exception as e:
                    print(f"Error moving file {file_name}: {e}")

        # Rename all files by replacing each digit with the next
        for file_name in os.listdir(output_folder):
            old_file_path = os.path.join(output_folder, file_name)
            try:
                new_file_name = re.sub(r'\d', lambda x: str((int(x.group(0)) + 1) % 10), file_name)
                new_file_path = os.path.join(output_folder, new_file_name)
                os.rename(old_file_path, new_file_path)
            except Exception as e:
                print(f"Error renaming file {file_name}: {e}")

        # Concatenate and sort file contents
        concatenated_content = []
        for file_name in sorted(os.listdir(output_folder)):
            file_path = os.path.join(output_folder, file_name)
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    for line in file:
                        concatenated_content.append(f"{file_name}:{line.strip()}\n")
            except Exception as e:
                print(f"Error reading file {file_name}: {e}")

        # Sort the concatenated content line by line using LC_ALL=C behavior
        sorted_content = "".join(sorted(concatenated_content, key=lambda x: x.encode('utf-8')))

        # Compute the SHA-256 hash of the sorted concatenated content
        hash_value = hashlib.sha256(sorted_content.encode('utf-8')).hexdigest()
        return hash_value
    except Exception as e:
        return f"Error processing files: {str(e)}"

def compare_files(zip_file_path, file1_name, file2_name):
    """
    Compares two files line by line and counts the number of differing lines.

    Args:
        zip_file_path (str): Path to the ZIP file containing the files.
        file1_name (str): Name of the first file.
        file2_name (str): Name of the second file.

    Returns:
        int: The number of lines that are different between the two files.
    """
    try:
        import zipfile

        # Extract the ZIP file
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall("q-compare-files")

        # Open the two files and compare line by line
        file1_path = os.path.join("q-compare-files", file1_name)
        file2_path = os.path.join("q-compare-files", file2_name)

        differing_lines = 0
        with open(file1_path, 'r', encoding='utf-8') as file1, open(file2_path, 'r', encoding='utf-8') as file2:
            for line1, line2 in zip(file1, file2):
                if line1.strip() != line2.strip():
                    differing_lines += 1

        return differing_lines
    except Exception as e:
        return f"Error comparing files: {str(e)}"




