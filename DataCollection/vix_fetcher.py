import os
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def fetch_today_vix_data():
    vix = yf.Ticker("^VIX")
    data = vix.history(period="1d")
    return data['Close'].iloc[0]

def convert_to_float(x):
    if x in ['#N/A', '', None]:
        return np.nan
    try:
        return float(x)
    except ValueError:
        print(f"Warning: Could not convert '{x}' to float. Returning NaN.")
        return np.nan

def save_to_postgresql(date, value):
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
        CREATE TABLE IF NOT EXISTS vix_data (
            date DATE PRIMARY KEY,
            value FLOAT
        );
        '''
        cursor.execute(create_table_query)
        conn.commit()
        print("Table 'vix_data' created or verified.")

        # Insert or update VIX data in the database
        insert_query = '''
        INSERT INTO vix_data (date, value)
        VALUES (%s, %s)
        ON CONFLICT (date) 
        DO UPDATE SET value = EXCLUDED.value;
        '''
        cursor.execute(insert_query, (date, value))
        
        conn.commit()
        print(f"VIX data for {date} inserted/updated in the database.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()
        print("Database connection closed.")

def main():
    current_date = datetime.now().date()
    vix_value = fetch_today_vix_data()
    vix_value = convert_to_float(vix_value)
    
    if not np.isnan(vix_value):
        save_to_postgresql(current_date, vix_value)
    else:
        print("Failed to fetch valid VIX data.")

if __name__ == '__main__':
    main()