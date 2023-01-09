
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

  # init variables
  ticks = 30 # number of ticks
  timeframe = "1s" # 1s, 1m
  profit = 0.05 # in percent
  risk_factor = 0.5 # 0.5 = 50% risk   2 take-profit / 1 stop-loss
  investment_percentage = 0.5 # 0.5 = 50% of the account balance
  trades = 5 # number of trades

  # symbol and timeframe
  symbol = "ETHBUSD"

  # start listening to data in a separate thread
  listen_process = Process(target=bot.listen_to_websocket)

  # start a separate thread to track the trades
  trade_process = Process(target=bot.track_trades)

  # start the threads
  listen_process.start()

  # Print a list of options
  quit = False
  while (not quit):
    print('##########################################################################################')
    print("Select between following Options.")
    print("1. Trading")
    print("2. Profit")
    print("3. Track Orders")
    print("4. Open Orders")
    print("5. All Orders")
    print("6. Reset")
    print("7. Exit")
    option = input("Enter the number corresponding to your choice: ")
    print('##########################################################################################')

    # Perform the selected option
    if option == "1":
      print("You selected Trading.")
      symbol_input = input("Enter the symbol (default = BTCUSDT): ")
      symbol = symbol_input or "BTCUSDT"

      timeframe_input = input("Enter the timeframe (1s, 1m, default = 1s): ")
      timeframe = timeframe_input or "1s"

      ticks_input = input("Enter the number of ticks (default = 30): ")
      ticks = int(ticks_input) if ticks_input else 30

      profit_input = input("Enter the profit in percent (default = 1%): ")
      profit = float(profit_input)/100 if profit_input else 0.01

      risk_factor_input = input("Enter the risk factor (0.5 = 50% risk -> 2 take-profit / 1 stop-loss, default = 1.0): ")
      risk_factor = float(risk_factor_input) if risk_factor_input else 1.0

      investment_percentage_input = input("Enter the investment percentage (0.5 = 50% of the account balance, default = 0.5): ")
      investment_percentage = float(investment_percentage_input) if investment_percentage_input else 0.5

      trades_input = input("Enter the number of trades (default = 5): ")
      trades = int(trades_input) if trades_input else 5

      # start a separate thread to process the data from the queue
      process_process = Process(target=bot.process_data, args=(symbol, timeframe, ticks, profit, risk_factor, investment_percentage, trades))


      print("You selected Trading with following parameters:")
      print("Symbol: ", symbol)
      print("Timeframe: ", timeframe)
      print("Ticks: ", ticks)
      print("Profit: ", profit)
      print("Risk Factor: ", risk_factor)
      print("Investment Percentage: ", investment_percentage)
      print("Trades: ", trades)


      process_process.start()
      trade_process.start()
      continue
    elif option == "2":
      print("You selected Profit.")
      symbol = input("Please select symbol: ")
      time.sleep(1)
      continue
    elif option == "3":
      print("You selected Track Orders.")
      bot.track_trades()
      time.sleep(1)
      continue
    elif option == "4":
      print("You selected Open Orders.")
      open_orders = bot.get_open_orders()
      for order in open_orders:
        print("Order: \n", "Symbol: ", order['symbol'], "Price: ", order['price'], "Quantity: ", order['origQty'], "Side: ", order['side'], "Status: ", order['status'])
      continue
    elif option == "5":
      print("You selected All Orders.")
      all_orders = bot.get_all_orders()
      for order in all_orders:
        print("Order: \n", "Symbol: ", order['symbol'], "Price: ", order['price'], "Quantity: ", order['origQty'], "Side: ", order['side'], "Status: ", order['status'])
      continue
    elif option == "6":
      print("You selected Reset.")
      bot.reset()
      continue
    elif option == "7":
      print("You selected Exit.")
      break
    else:
      print("Invalid option.")
      continue

  

  # wait for the threads to finish
  listen_process.join()
  process_process.join()
  trade_process.join()

  # monitor the performance of the system
  while True:
      time.sleep(1)


