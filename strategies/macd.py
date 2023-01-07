import ta
import pandas as pd
from binance.client import Client

def macd_strategy(prices, fast_period=12, slow_period=26, signal_period=9):

    # Calculate the moving average convergence divergence (MACD)
    macd = ta.trend.macd(prices, window_fast=fast_period, window_slow=slow_period, fillna=True)

    # Calculate the MACD signal
    macd_signal = ta.trend.macd_signal(prices, window_fast=fast_period, window_slow=slow_period, window_sign=signal_period, fillna=True)

    # Create a DataFrame to store the MACD and MACD signal
    df = pd.DataFrame({'MACD': macd, 'MACD_Signal': macd_signal})

    # Create a function to buy (1) or sell (-1) or hold (0) based on the MACD and MACD signal
    def get_signal(row):
        if row['MACD'] > row['MACD_Signal']:
            return Client.SIDE_BUY  # buy
        elif row['MACD'] < row['MACD_Signal']:
            return Client.SIDE_SELL # sell

    # Apply the buy/sell function to the DataFrame
    df['Signal'] = df.apply(get_signal, axis=1)

    return df

