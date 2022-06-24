# -*- coding: utf-8 -*-
"""crypto realtime.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1tnTZ0POqXSsQD2UAw2rIcoBNG8rIYvns

## This code is Finalterm's real-time trading phase.

# Import
"""

!pip install python-binance # This is an unofficial Python wrapper for the Binance exchange REST API v3.
import pandas as pd # Python Data Analysis Library
from binance.client import Client # Creating a client
from binance_keys import api_key, secret_key # Issued from a personal account to use binance data
from datetime import datetime, timedelta # Time data
import time # Time data
from binance.exceptions import * #Import all (*) from the os module

client = Client(api_key, secret_key,tld='us') # Binance Korean server is terminated and designated as us

"""# Bolinger band function

"""

def sma(data, window): # Moving average
  return(data.rolling(window = window).mean()) # Average the closing price during the window

def bollinger_band(data, sma, window, nstd): 
    std = data.rolling(window = window).std() # Number of standard deviation (typically 2)
    upper_band = sma + std * nstd # nstd is Standard deviation over last n periods 
    lower_band = sma - std * nstd 

    return upper_band, lower_band

"""# Data collection and Bolinger band creation"""

symbols = ['BTC','ETH','LTC'] # Symbol string 
start_n_hours_ago = 48

# Data collection
def gather_data(symbols, start_n_hours_ago): 
    merge = False
    for symbol in symbols: 
      # Get Historical Klines from Binance, symbol: Name of symbol pair, interval : Binance Kline interval, start_str : optional - Start date string in UTC format or timestamp in milliseconds
      # Returns : list of OHLCV values (Open time, Open, High, Low, Close, Volume, Close time, Quote asset volume, Number of trades, Taker buy base asset volume, Taker buy quote asset volume, Ignore)
        klines = client.get_historical_klines(symbol=f'{symbol}USDT',
                                              interval=client.KLINE_INTERVAL_1HOUR, 
                                              start_str=str(datetime.now()-timedelta(hours=start_n_hours_ago)))
        cols = ['OpenTime',
                f'{symbol}-USD_Open',
                f'{symbol}-USD_High',
                f'{symbol}-USD_Low',
                f'{symbol}-USD_Close',
                f'{symbol}-USD_volume', #
                'CloseTime',
                f'{symbol}-QuoteAssetVolume',
                f'{symbol}-NumberOFTrades',
                f'{symbol}-TBBAV',
                f'{symbol}-TBQAV',
                f'{symbol}-ignore']

        df = pd.DataFrame(klines,columns=cols)

        if merge == True:
            dfs = pd.merge(df,dfs,how='inner',on=['OpenTime','CloseTime'])
        else :
            dfs = df
            merge = True

    dfs['OpenTime'] = [datetime.fromtimestamp(ts/1000) for ts in dfs['OpenTime']]
    dfs['CloseTime'] = [datetime.fromtimestamp(ts/1000) for ts in dfs['CloseTime']]     
   
    for col in dfs.columns :
        if not 'Time' in col:
            dfs[col] = dfs[col].astype(float)

# Bolinger band creation
    for symbol in symbols:
        dfs[f'{symbol}_sma'] = sma(dfs[f'{symbol}-USD_Close'],window=20)
        dfs[f'{symbol}_upper_band'], dfs[f'{symbol}_lower_band'] = bollinger_band(data=dfs[f'{symbol}-USD_Close'],
                                                                                  sma=dfs[f'{symbol}_sma'],
                                                                                  window=20, #window is Number of days in smoothing period
                                                                                  nstd=3)
    
    dfs.dropna(inplace=True)

    return dfs

"""# Check the collected data


"""

df = gather_data(symbols,48)
df

def get_states(df, symbols):
    states = {}

    for symbol in symbols:
        if df[f'{symbol}-USD_Close'].iloc[-1] < df[f'{symbol}_lower_band'].iloc[-1]: #If it is lower than the Bollinger Band
            states[symbol] = 'below'
        elif df[f'{symbol}-USD_Close'].iloc[-1] > df[f'{symbol}_upper_band'].iloc[-1]:#If it is upper than the Bollinger Band
            states[symbol] = 'above'
        else:
            states[symbol] = 'inside'
            
    return states

"""# Real-time transaction"""

balance_unit = 'USDT' 
first = True

while True: 
    if (datetime.now().second % 10 == 0) or first: 
        if (datetime.now().minute == 0 and datetime.now().second == 10) or first:
            # refresh data 
            first = False 
            df = gather_data(symbols,48) 
            states = get_states(df,symbols)
            print('Current state of the market:')
            print(states)
        try:
            print('\n') 
            if balance_unit == 'USDT' : # Looking to buy
                for symbol in symbols: 
                    ask_price = float(client.get_orderbook_ticker(symbol = f'{symbol}USDT')['askPrice']) 
                    lower_band = df[f'{symbol}_lower_band'].iloc[-1] 
                    print(datetime.now())
                    print(f'{symbol} : ask price {ask_price} | lower band {lower_band}') 
                    if ask_price < lower_band and states[symbol] == 'inside': # Buy signal 
                        print('buy') 
                        balance_unit = symbol 
                        break

            if balance_unit != 'USDT': # Looking to sell
                bid_price = float(client.get_orderbook_ticker(symbol = f'{balance_unit}USDT')['bidPrice'])
                upper_band = df[f'{balance_unit}_upper_band'].iloc[-1] 
                if bid_price > upper_band and states[balance_unit] == 'inside': # Sell signal 
                    print('sell') 
                    balance_unit = 'USDT' 

            time.sleep(1) 
        # Set exception to prevent transaction from being stopped due to disruption
        except BinanceAPIException as e: 
          print(e.status_code)
          print(e.message)