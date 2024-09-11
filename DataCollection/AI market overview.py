import os
import yfinance as yf
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv  # To load environment variables
from datetime import datetime
import pandas as pd  # Import pandas for moving average calculations

# Load environment variables from .env file
load_dotenv()

# Database credentials
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

# OpenAI API key setup
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Function to fetch market data and calculate moving averages
def get_market_data_with_moving_averages(tickers):
    market_data = {}
    for ticker in tickers:
        stock = yf.Ticker(ticker)
        try:
            # Use "3mo" to fetch the last 3 months of historical data for moving average calculations
            hist = stock.history(period="3mo")
            
            if hist.empty:
                raise ValueError(f"Keine Daten für {ticker} verfügbar")

            # Calculate the 5-day, 20-day, and 50-day moving averages
            hist['MA5'] = hist['Close'].rolling(window=5).mean()
            hist['MA20'] = hist['Close'].rolling(window=20).mean()
            hist['MA50'] = hist['Close'].rolling(window=50).mean()

            # Get the latest available data
            latest = hist.iloc[-1]

            # Check trend direction based on moving averages
            if latest['Close'] < latest['MA5'] and latest['Close'] < latest['MA20']:
                trend = 'falling'
            elif latest['Close'] > latest['MA5'] and latest['Close'] > latest['MA20']:
                trend = 'rising'
            else:
                trend = 'neutral'

            market_data[ticker] = {
                'Name': stock.info.get('longName', 'Unknown'),
                'Last Price': latest['Close'],
                'Change': latest['Close'] - latest['Open'],
                'Percent Change': ((latest['Close'] - latest['Open']) / latest['Open']) * 100,
                'MA5': latest['MA5'],
                'MA20': latest['MA20'],
                'MA50': latest['MA50'],
                'Trend': trend
            }

            # Output the data for checking
            print(f"\n{ticker} Data:")
            print(f"Name: {stock.info.get('longName', 'Unknown')}")
            print(f"Last Price: {latest['Close']}")
            print(f"Change: {latest['Close'] - latest['Open']}")
            print(f"Percent Change: {((latest['Close'] - latest['Open']) / latest['Open']) * 100}")
            print(f"5-Day MA: {latest['MA5']}, 20-Day MA: {latest['MA20']}, 50-Day MA: {latest['MA50']}")
            print(f"Trend: {trend}\n")

        except Exception as e:
            print(f"Fehler bei {ticker}: {e}")
            market_data[ticker] = {
                'Name': stock.info.get('longName', 'Unknown'),
                'Last Price': 'N/A',
                'Change': 'N/A',
                'Percent Change': 'N/A',
                'MA5': 'N/A',
                'MA20': 'N/A',
                'MA50': 'N/A',
                'Trend': 'N/A'
            }
    return market_data

# Function to generate a concise interpretation focusing only on notable trends
def format_data_for_llm(market_data):
    trends = []
    for ticker, data in market_data.items():
        name = data['Name']
        trend = data['Trend']

        if trend == 'falling':
            trends.append(f"{name} zeigt eine Abwärtsbewegung.")
        elif trend == 'rising':
            trends.append(f"{name} zeigt eine Aufwärtsbewegung.")
        elif trend == 'neutral':
            trends.append(f"{name} zeigt keine signifikante Bewegung.")

    # Output what will be sent to LLM for checking
    print(f"\nFormatted data for LLM: {' '.join(trends)}\n")

    # If no notable trends, return a default message
    if not trends:
        return "Der Markt zeigt derzeit keine signifikanten Bewegungen."
    else:
        return " ".join(trends)

# Function to generate a concise market interpretation in simple language
def generate_llm_interpretation(market_data_text):
    prompt = f"""
    Basierend auf den folgenden aktuellen Marktdaten und den erkannten Trends:

    {market_data_text}

    Erstelle eine kurze, prägnante Analyse (maximal 3-4 Sätze) des globalen Marktgeschehens. Beachte dabei:
    1. Fasse die allgemeinen Trends zusammen, ohne spezifische Indizes oder Werte zu nennen.
    2. Hebe nur die wichtigsten übergreifenden Bewegungen hervor.
    3. Biete einen tieferen Einblick oder eine mögliche Erklärung für diese Trends, die für Privatanleger nicht offensichtlich sein könnte.
    4. Wenn möglich, gib einen Ausblick auf mögliche zukünftige Entwicklungen.
    """

    # Output what will be sent to OpenAI API
    print(f"\nPrompt sent to OpenAI API:\n{prompt}\n")

    # Use the correct chat-based model endpoint with reduced tokens for a concise output
    response = client.chat.completions.create(
        model="gpt-4o",  # or "gpt-4" if available to you
        messages=[
            {"role": "system", "content": "Du bist ein erfahrener Börsenanalyst, der komplexe Marktdaten in kurze, aussagekräftige Einblicke umwandelt."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=800,  # Further reduced for more concise output
        temperature=0.7,
    )

    # Output the response from OpenAI for checking
    print(f"\nResponse from OpenAI API:\n{response.choices[0].message.content}\n")
    
    return response.choices[0].message.content

# Function to store the market overview in the PostgreSQL database
def store_in_database(market_summary):
    try:
        # Connect to PostgreSQL database
        connection = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = connection.cursor()
        
        # SQL query to insert the market summary
        insert_query = """
        INSERT INTO market_overview (market_summary)
        VALUES (%s);
        """
        cursor.execute(insert_query, (market_summary,))
        
        # Commit the transaction
        connection.commit()
        
        print("Marktübersicht erfolgreich in die Datenbank geschrieben.")
    
    except Exception as error:
        print(f"Fehler beim Schreiben in die Datenbank: {error}")
    
    finally:
        # Close the database connection
        if connection:
            cursor.close()
            connection.close()

# List of tickers for a broader market view, including sector ETFs
tickers = [
    '^GSPC',  # S&P 500
    '^DJI',   # Dow Jones
    '^IXIC',  # NASDAQ
    '^RUT',   # Russell 2000
    '^GDAXI', # DAX (Germany)
    '^FTSE',  # FTSE 100 (UK)
    '^N225',  # Nikkei 225 (Japan)
    '^HSI',   # Hang Seng (Hong Kong)
    'GC=F',   # Gold
    'SI=F',   # Silver
    'CL=F',   # Crude Oil WTI
    'EURUSD=X', # Euro to USD exchange rate
    'JPY=X',   # Japanese Yen to USD
    'BTC-USD', # Bitcoin
    'ETH-USD', # Ethereum
    '^TNX',   # 10-Year U.S. Treasury Yield
    '^VIX',   # Volatility Index
    # Sector ETFs
    'QQQ',    # Technology - Invesco QQQ Trust
    'XLE',    # Energy - Energy Select Sector SPDR Fund
    'XLF',    # Financials - Financial Select Sector SPDR Fund
    'XLV',    # Healthcare - Health Care Select Sector SPDR Fund
    'XLP',    # Consumer Staples - Consumer Staples Select Sector SPDR Fund
    'XLY',    # Consumer Discretionary - Consumer Discretionary Select Sector SPDR Fund
    'XLI',    # Industrials - Industrial Select Sector SPDR Fund
    'XLRE',   # Real Estate - Real Estate Select Sector SPDR Fund
    'SOXX',   # Semiconductors - iShares Semiconductor ETF
]

# Fetch market data with moving averages
market_data = get_market_data_with_moving_averages(tickers)

# Format the data for LLM
formatted_market_data = format_data_for_llm(market_data)

# Generate longer-term trend analysis using LLM
llm_interpretation = generate_llm_interpretation(formatted_market_data)

# Output the LLM's analysis
print("Marktübersicht erstellt durch das LLM:\n")
print(llm_interpretation)

# Store the market overview in the PostgreSQL database
store_in_database(llm_interpretation)