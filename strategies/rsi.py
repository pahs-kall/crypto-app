from binance.client import Client

def calculate_rsi(ds, periods = 14, ema = True):
    """
    Returns a pd.Series with the relative strength index.
    """

    close_delta = ds.diff()

    # Make two series: one for lower closes and one for higher closes
    up = close_delta.clip(lower=0)
    down = -1 * close_delta.clip(upper=0)
    
    if ema == True:
	    # Use exponential moving average
        ma_up = up.ewm(com = periods - 1, adjust=True, min_periods = periods).mean()
        ma_down = down.ewm(com = periods - 1, adjust=True, min_periods = periods).mean()
    else:
        # Use simple moving average
        ma_up = up.rolling(window = periods, adjust=False).mean()
        ma_down = down.rolling(window = periods, adjust=False).mean()
        
    rsi = ma_up / ma_down
    rsi = 100 - (100/(1 + rsi))
    
    return rsi

def decide_on_order(rsi, macd):

  print("RSI: ", rsi)
  print("MACD: ", macd)
  
  if macd == Client.SIDE_SELL and rsi == Client.SIDE_SELL:
    return Client.SIDE_SELL
  elif macd == Client.SIDE_BUY and rsi == Client.SIDE_BUY:
    return Client.SIDE_BUY


