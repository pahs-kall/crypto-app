import config, csv
from binance.client import Client

def update_data(symbols, interval, start_date, end_date):

  client = Client(config.API_KEY, config.API_SECRET)

  # prices = client.get_all_tickers()

  # for price in prices:
  #     print(price)

  for symbol in symbols:
    # filename = 'BTCUSDT_1day.csv'
    file_name = symbol + '_' + interval + '.csv'

    # interval = Client.KLINE_INTERVAL_1DAY ...
    if interval == '1m':
      interval = Client.KLINE_INTERVAL_1MINUTE
    elif interval == '3m':
      interval = Client.KLINE_INTERVAL_3MINUTE
    elif interval == '5m':
      interval = Client.KLINE_INTERVAL_5MINUTE
    elif interval == '15m':
      interval = Client.KLINE_INTERVAL_15MINUTE
    elif interval == '30m':
      interval = Client.KLINE_INTERVAL_30MINUTE
    elif interval == '1h':
      interval = Client.KLINE_INTERVAL_1HOUR
    elif interval == '2h':
      interval = Client.KLINE_INTERVAL_2HOUR
    elif interval == '4h':
      interval = Client.KLINE_INTERVAL_4HOUR
    elif interval == '6h':
      interval = Client.KLINE_INTERVAL_6HOUR
    elif interval == '8h':
      interval = Client.KLINE_INTERVAL_8HOUR
    elif interval == '12h':
      interval = Client.KLINE_INTERVAL_12HOUR
    elif interval == '1d':
      interval = Client.KLINE_INTERVAL_1DAY
    elif interval == '3d':
      interval = Client.KLINE_INTERVAL_3DAY
    elif interval == '1w':
      interval = Client.KLINE_INTERVAL_1WEEK
    elif interval == '1M':
      interval = Client.KLINE_INTERVAL_1MONTH


    csvfile = open(file_name, 'w', newline='') 
    candlestick_writer = csv.writer(csvfile, delimiter=',')

    candlesticks = client.get_historical_klines(symbol, interval, start_date, end_date)
    #candlesticks = client.get_historical_klines("BTCUSDT", Client.KLINE_INTERVAL_1DAY, "1 Jan, 2020", "12 Jul, 2020")
    #candlesticks = client.get_historical_klines("BTCUSDT", Client.KLINE_INTERVAL_1DAY, "1 Jan, 2017", "12 Jul, 2020")

    for candlestick in  candlesticks:
        candlestick[0] = candlestick[0] / 1000
        candlestick_writer.writerow(candlestick)

    csvfile.close()