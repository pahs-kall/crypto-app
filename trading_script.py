
from trading_algo import TradingBot
from multiprocessing import Process
from secret import TEST_API_KEY, TEST_SECRET_KEY
import stream.db as db
import time

if __name__ == '__main__':
  # create an instance of the TradingBot class
  bot = TradingBot(TEST_API_KEY, TEST_SECRET_KEY)

  # init db
  db.init_db()

  # get the current balance of the trading account
  bot.get_account_balance()
  bot.get_exchange_info()

  # ticks of last ema data to use
  ticks = 30
  timeframe = "1s"

  # wanted profit per trade / risk_factor
  profit = 0.1 # in percent
  risk_factor = 0.5 # 0.5 = 50% risk   2 take-profit / 1 stop-loss
  investment_percentage = 0.5

  # symbol and timeframe
  symbol = "ETHBUSD"

  # start listening to data in a separate thread
  listen_process = Process(target=bot.listen_to_websocket)

  # start a separate thread to process the data from the queue
  process_process = Process(target=bot.process_data, args=(symbol, timeframe, ticks, profit, risk_factor, investment_percentage))

  track_process = Process(target=bot.track_profit)

  # start the threads
  listen_process.start()

  # wait for user input to start the process thread
  print('##########################################################################################')
  input("Press Enter to start the trading...")
  print("Starting trading...")
  print('##########################################################################################')
  process_process.start()

  # track the profit
  track_process.start()

  # wait for the threads to finish
  listen_process.join()
  process_process.join()
  track_process.join()

  # monitor the performance of the system
  while True:
      time.sleep(1)


