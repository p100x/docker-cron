import os
import pandas as pd
import numpy as np
from google.oauth2 import service_account
from googleapiclient.discovery import build
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def authenticate():
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), 'service_account.json')

    creds = None
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    else:
        print("Service account file not found.")
    return creds

def fetch_sheet_data(creds):
    SAMPLE_SPREADSHEET_ID = '14Om8hHNuufjWj7dsFKLkpwHH1zuYQ31hIghUJUODn5Q'
    SAMPLE_RANGE_NAME = 'Sheet1!A1:M'  # Adjust this range according to your sheet

    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()

    result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                range=SAMPLE_RANGE_NAME).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
        return None
    else:
        print(f"Fetched {len(values)} rows of data.")
        return values

def convert_to_float(x, is_percentage=False):
    if x in ['#N/A', '', None]:
        return np.nan
    x = x.replace('.', '')  # Remove periods (thousand separators)
    x = x.replace(',', '.')  # Replace comma with dot for decimal conversion
    x = x.rstrip('%')
    try:
        value = float(x)
        return value / 100 if is_percentage else value
    except ValueError:
        print(f"Warning: Could not convert '{x}' to float. Returning NaN.")
        return np.nan

def process_aaii_data(data):
    # Convert the data into a pandas DataFrame
    df = pd.DataFrame(data[1:], columns=data[0])  # Assuming first row is header

    # Standardize column names
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

    print("\nColumns after renaming:", df.columns)

    if 'reported_date' not in df.columns:
        print("Error: 'reported_date' column not found. Please check the column names.")
        return None

    # Convert percentage columns to float
    for col in ['bullish', 'neutral', 'bearish']:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: convert_to_float(x, is_percentage=True))

    # Convert other columns to float
    for col in ['bull_bear_spread', 's&p500_weekly_close']:
        if col in df.columns:
            df[col] = df[col].apply(convert_to_float)

    # Convert 'reported_date' to datetime format
    df['reported_date'] = pd.to_datetime(df['reported_date'], format='%m-%d-%y')

    # Sort by date
    df = df.sort_values('reported_date')

    print("\nProcessed dataframe:")
    print(df.head())
    print("\nColumns after processing:", df.columns)

    # Verify and print the last few rows to ensure all data is included
    print("\nLast few rows of the processed DataFrame:")
    print(df.tail())

    return df

def save_to_postgresql(df):
    # Database connection parameters
    conn_params = {
        'dbname': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT'),
        'sslmode': os.getenv('DB_SSLMODE')
    }
    
    # Establish a connection to the database
    try:
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        print("Database connection established.")
        
        # Create table if it doesn't exist
        create_table_query = '''
        CREATE TABLE IF NOT EXISTS aaii_sentiment_data (
            reported_date DATE PRIMARY KEY,
            bullish FLOAT,
            neutral FLOAT,
            bearish FLOAT,
            bull_bear_spread FLOAT,
            s_p500_weekly_close FLOAT
        );
        '''
        cursor.execute(create_table_query)
        conn.commit()
        print("Table 'aaii_sentiment_data' created or verified.")

        # Insert or update DataFrame records in the database
        for i, row in df.iterrows():
            insert_query = '''
            INSERT INTO aaii_sentiment_data (reported_date, bullish, neutral, bearish, bull_bear_spread, s_p500_weekly_close)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (reported_date) 
            DO UPDATE SET
                bullish = EXCLUDED.bullish,
                neutral = EXCLUDED.neutral,
                bearish = EXCLUDED.bearish,
                bull_bear_spread = EXCLUDED.bull_bear_spread,
                s_p500_weekly_close = EXCLUDED.s_p500_weekly_close;
            '''
            # Convert the row to a tuple ensuring the values are correctly converted
            cursor.execute(insert_query, (row['reported_date'], row['bullish'], row['neutral'], row['bearish'], row['bull_bear_spread'], row['s&p500_weekly_close']))
        
        conn.commit()
        print(f"{len(df)} records inserted/updated in the database.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()
        print("Database connection closed.")

def main():
    creds = authenticate()
    if not creds:
        print("Authentication failed.")
        return
    data = fetch_sheet_data(creds)
    if data:
        df = process_aaii_data(data)
        if df is not None:
            save_to_postgresql(df)
        else:
            print("Failed to process data.")
    else:
        print("No data found or error occurred.")

if __name__ == '__main__':
    main()
