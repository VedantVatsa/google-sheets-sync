import os
import mysql.connector
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Google Sheets API Credentials
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_info({
    'type': 'service_account',
    'project_id': os.getenv('GOOGLE_PROJECT_ID'),
    'private_key_id': os.getenv('PRIVATE_KEY_ID'),  # You may need to add this to your .env
    'private_key': os.getenv('GOOGLE_PRIVATE_KEY').replace('\\n', '\n'),
    'client_email': os.getenv('GOOGLE_CLIENT_EMAIL'),
    'client_id': os.getenv('CLIENT_ID'),  # You may need to add this to your .env
    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
    'token_uri': 'https://oauth2.googleapis.com/token',
    'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
    'client_x509_cert_url': f"https://www.googleapis.com/robot/v1/metadata/x509/{os.getenv('GOOGLE_CLIENT_EMAIL')}",
})

service = build('sheets', 'v4', credentials=creds)
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')

# MySQL connection
db = mysql.connector.connect(
    host=os.getenv('MYSQL_HOST'),
    user=os.getenv('MYSQL_USER'),
    password=os.getenv('MYSQL_PASSWORD'),
    database=os.getenv('MYSQL_DATABASE')
)

cursor = db.cursor()

# Create the table (if it doesn't exist yet)
cursor.execute("""
CREATE TABLE IF NOT EXISTS student (
    name VARCHAR(255),
    reg_no VARCHAR(255) PRIMARY KEY
);
""")

# Insert data function
def insert_data(name, reg_no):
    cursor.execute("INSERT INTO student (name, reg_no) VALUES (%s, %s)", (name, reg_no))
    db.commit()

# Update data function
def update_data(name, reg_no):
    cursor.execute("UPDATE student SET name = %s WHERE reg_no = %s", (name, reg_no))
    db.commit()
    print(f"Updated entry for reg_no {reg_no} to name {name}.")

# Delete data function
def delete_data(reg_no):
    cursor.execute("DELETE FROM student WHERE reg_no = %s", (reg_no,))
    db.commit()
    print(f"Deleted entry for reg_no {reg_no}.")

def fetch_data_from_sheet():
    # Access the spreadsheet
    RANGE_NAME = 'Sheet1!A1:B10'  # Adjust this range according to your sheet
    sheet = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = sheet.get('values', [])
    return values

def fetch_existing_data_from_db():
    # Fetch all existing data from the student table
    cursor.execute("SELECT name, reg_no FROM student")
    return cursor.fetchall()

def sync_db_to_sheets():
    # Fetch all data from the student table
    cursor.execute("SELECT name, reg_no FROM student")
    rows = cursor.fetchall()

    # Prepare the data for Google Sheets
    data = [['Name', 'Registration No']] + list(rows)

    # Update the Google Sheet
    body = {
        'values': data
    }
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range='Sheet1!A1:B',  # Adjust this range according to your sheet
        valueInputOption='RAW',
        body=body
    ).execute()

    print("Data from database synced to Google Sheets.")

# Main function to fetch from Google Sheets and insert/update/delete in MySQL
def sync_data():
    # Fetch existing data from the database
    existing_data = fetch_existing_data_from_db()
    existing_dict = {reg_no: name for name, reg_no in existing_data}  # Map reg_no to name

    # Fetch data from Google Sheets
    data = fetch_data_from_sheet()

    # Create a mapping from Google Sheets data
    sheet_dict = {}
    for row in data[1:]:  # Skip the header row
        if len(row) >= 2:
            sheet_dict[row[1]] = row[0]  # Map reg_no to name

    # Insert or update rows from Google Sheets into MySQL
    for reg_no, name in sheet_dict.items():
        if reg_no not in existing_dict:
            insert_data(name, reg_no)  # Insert new entry
        elif existing_dict[reg_no] != name:
            update_data(name, reg_no)  # Update existing entry

    # Detect and mark deletions
    for reg_no in existing_dict.keys():
        if reg_no not in sheet_dict:
            print(f"Data with reg_no {reg_no} needs to be removed from MySQL.")
            confirmation = input(f"Do you want to delete entry with reg_no {reg_no}? (y/n): ")
            if confirmation.lower() == 'y':
                delete_data(reg_no)  # Remove entry from MySQL

    # Sync updated database back to Google Sheets
    sync_db_to_sheets()  # Push the updated database to Google Sheets

# Example usage
if __name__ == "__main__":
    sync_data()  # Synchronize data between Google Sheets and MySQL


