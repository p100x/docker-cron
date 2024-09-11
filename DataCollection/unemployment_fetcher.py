import os
import requests
import numpy as np
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Dein FRED API Key
FRED_API_KEY = '38b77fb80b25db65fbcf1c011882cc05'

def fetch_unemployment_data():
    # Berechne das Startdatum (heute minus 2 Jahre) und das Enddatum (heute)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=2*365)).strftime('%Y-%m-%d')
    
    # URL für die FRED API-Anfrage
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id=UNRATE&api_key={FRED_API_KEY}&file_type=json&observation_start={start_date}&observation_end={end_date}"
    print(url)  # Debugging: Ausgabe der URL
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()['observations']
        return [(item['date'], convert_to_float(item['value'])) for item in data]
    else:
        print(f"Failed to fetch unemployment data: {response.status_code}")
        print(response.text)  # Debugging: Ausgabe der Fehlermeldung
        return []

# Funktion zum Konvertieren der Werte in Float, Fehlerbehandlung eingeschlossen
def convert_to_float(x):
    if x in ['#N/A', '', None]:
        return np.nan
    try:
        return float(x)
    except ValueError:
        print(f"Warning: Could not convert '{x}' to float. Returning NaN.")
        return np.nan

# Funktion zum Speichern der Daten in PostgreSQL
def save_to_postgresql(date, value):
    conn = None
    cursor = None

    # Datenbankverbindungsparameter aus der .env Datei laden
    conn_params = {
        'dbname': 'defaultdb',
        'user': 'doadmin',
        'password': 'AVNS_jLt-zgoBMSLpZW7nTnW',
        'host': 'kundendaten-do-user-17520555-0.d.db.ondigitalocean.com',
        'port': '25060',
        'sslmode': 'require'  # SSL-Verbindung wird benötigt
    }
    
    try:
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        print("Database connection established.")
        
        # Tabelle für Arbeitslosenquote erstellen, falls sie noch nicht existiert
        create_table_query = '''
        CREATE TABLE IF NOT EXISTS unemployment_data (
            date DATE PRIMARY KEY,
            value FLOAT
        );
        '''
        cursor.execute(create_table_query)
        conn.commit()
        print("Table 'unemployment_data' created or verified.")

        # Daten in die Tabelle einfügen oder aktualisieren, falls der Datensatz bereits existiert
        insert_query = '''
        INSERT INTO unemployment_data (date, value)
        VALUES (%s, %s)
        ON CONFLICT (date) 
        DO UPDATE SET value = EXCLUDED.value;
        '''
        cursor.execute(insert_query, (date, value))
        
        conn.commit()
        print(f"Unemployment data for {date} inserted/updated in the database.")

    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print("Database connection closed.")

def main():
    # Arbeitslosendaten abrufen
    unemployment_data = fetch_unemployment_data()
    
    # Arbeitslosendaten in die Datenbank speichern
    for date, value in unemployment_data:
        if not np.isnan(value):
            save_to_postgresql(date, value)
        else:
            print(f"Invalid data for {date}, skipping.")

if __name__ == '__main__':
    main()
