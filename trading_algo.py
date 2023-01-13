from constants import *
from strategies.macd import macd_strategy
from strategies.rsi import calculate_rsi, decide_on_order
from binance.client import Client
from binance.enums import *
from stream.binance_streamer import run_stream
import csv
import os
import time
import math
import shutil
import pandas as pd
from datetime import datetime
from threading import Thread
from binance.helpers import round_step_size

class TradingBot:
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.client = Client(api_key, api_secret, testnet=True)

    def get_account_balance(self):
        # make a GET request to the API to get the current balance of the trading account
        account = self.client.get_account()

        balances = account['balances']

        # Create the table header
        table = "+------------------+------------+------------+\n"
        table += "|      Asset       |   Free     |   Locked   |\n"
        table += "+------------------+------------+------------+\n"

        # Add each data item to the table
        for item in balances:
            # Round the values to two decimal places
            free = round(float(item['free']), 2)
            locked = round(float(item['locked']), 2)

            # Add the rounded values to the table, specifying a column width of 10 characters
            table += "| {:<16} | {:<10} | {:<10} |\n".format(item['asset'], free, locked)

        # Add the footer to the table
        table += "+------------------+------------+------------+\n"

        # Print the table
        print(table)

        return balances

    def get_exchange_info(self):
        # get exchange info
        exchange_info = self.client.get_exchange_info()
        for symbol in exchange_info.get('symbols'):
            print(symbol.get('symbol'), symbol.get('baseAsset'))
        print()

        return exchange_info

    def get_asset(self, pair):
        # get exchange info
        exchange_info = self.client.get_exchange_info()
        for symbol in exchange_info.get('symbols'):
            if symbol.get('symbol') == pair:
                return symbol.get('baseAsset')

    def track_trades(self):
      with open('data/trading/order_mapping.csv', 'r') as csvfile:
        reader = csv.reader(csvfile)
        order_mapping = list(reader)
      csvfile.close()
      
      orders = []
      symbol = ""
      
      # iterate through orders and check status
      for order in order_mapping:
        if order != []:
          symbol = order[0]

          order_orig = self.client.get_order(symbol=symbol, orderId=int(order[1]))
          oco_order_low = self.client.get_order(symbol=symbol, orderId=int(order[2]))
          oco_order_high = self.client.get_order(symbol=symbol, orderId=int(order[3]))

          new_order = [order_orig['orderId'], order_orig['status'], order_orig['origQty'], order_orig['price'], order_orig['side'], oco_order_low['orderId'], oco_order_low['status'], oco_order_high['orderId'], oco_order_high['status']]
          
          with open('data/trading/orders_' + symbol + '.csv', 'a+') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(new_order)
          csvfile.close()

      print('##########################################################################################')
      print("##################################  Orders tracked  ######################################")
      print('##########################################################################################')
      print()

    def track_profit(self, symbol):
      with open('data/trading/orders_' + symbol + '.csv', 'r') as csvfile:
        reader = csv.reader(csvfile)
        orders = list(reader)

      csvfile.close()

      first_run_done = False

      profit_sum = 0

      # iterate through orders and check status
      for order in orders:
        if order != []:

          message = ''
          profit = 0
          non_tracked_orders = 0

          order_orig = self.client.get_order(symbol=symbol, orderId=order[0])
          oco_order_low = self.client.get_order(symbol=symbol, orderId=order[5])
          oco_order_high = self.client.get_order(symbol=symbol, orderId=order[7])

          if order_orig['status'] == 'FILLED' and order_orig['side'] == 'BUY':
            if oco_order_low['status'] == 'FILLED':
              profit = float(oco_order_low['cummulativeQuoteQty']) - float(order_orig['cummulativeQuoteQty'])
              message = "Loss: " + str(profit) + " trading " + symbol + " on " + order_orig['side'] + " with " + order_orig['price'] + " sold at " + oco_order_low['price']
            elif oco_order_high['status'] == 'FILLED':
              profit = float(oco_order_high['cummulativeQuoteQty']) - float(order_orig['cummulativeQuoteQty'])
              message = "Profit: " + str(profit) + " trading " + symbol + " on " + order_orig['side'] + " with " + order_orig['price'] + " sold at " + oco_order_high['price']
            else:
              non_tracked_orders += 1
          elif order_orig['status'] == 'FILLED' and order_orig['side'] == 'SELL':
            if oco_order_low['status'] == 'FILLED':
              profit = float(order_orig['cummulativeQuoteQty']) - float(oco_order_low['cummulativeQuoteQty'])
              message = "Loss: " + str(profit) + " trading " + symbol + " on " + order_orig['side'] + " with " + order_orig['price'] + " bought at " + oco_order_low['price']
            elif oco_order_high['status'] == 'FILLED':
              profit = float(order_orig['cummulativeQuoteQty']) - float(oco_order_high['cummulativeQuoteQty'])
              message = "Profit: " + str(profit) + " trading " + symbol + " on " + order_orig['side'] + " with " + order_orig['price'] + " bought at " + oco_order_high['price']
            else:
              non_tracked_orders += 1

          if non_tracked_orders != 0:
            return non_tracked_orders

          if message == '':
            return None

          if profit == 0:
            return None

          # append order to profit history
          with open('data/trading/profit_history_' + symbol + '.csv', 'a+') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([message])
          csvfile.close()

          cumulative_profit = 0

          if not first_run_done:
            # create file if not exists
            with open('data/trading/profit_' + symbol + '.csv', 'w+') as csvfile:
              pass
            csvfile.close()

            first_run_done = True

          # append cumulative profit
          with open('data/trading/profit_' + symbol + '.csv', 'a+') as csvfile:
            reader = csv.reader(csvfile)
            data = list(reader)
            cumulative_profit = math.fsum(data)
          csvfile.close()

          with open('data/trading/profit_' + symbol + '.csv', 'a+') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([float(cumulative_profit + profit)])
          csvfile.close()

          profit_sum = profit_sum + profit

      print('##########################################################################################') 
      print("Profit: " + str(cumulative_profit))
      print('##########################################################################################')
      print()

      print('##########################################################################################')
      print("##################################  Profit tracked  ######################################")
      print('##########################################################################################')
      print()

    def archive_files(self, symbol):
      files = ['orders_' + symbol + '.csv', 'profit_history_' + symbol + '.csv', 'profit_' + symbol + '.csv', 'order_mapping.csv']
      file_folder = 'data/trading/'

      archive_folder = 'data/trading/archive'

      # Get current timestamp
      timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
      # Create folder with timestamp as name
      os.makedirs(archive_folder + '/' + timestamp)
      # Iterate through files and move them to the new folder
      for file in files:
          if os.path.isfile(file_folder + file):
              shutil.move(file_folder + file, archive_folder + '/' + timestamp)

      print('##########################################################################################')
      print("Files have been archived to", archive_folder + '/' + timestamp)
      print('##########################################################################################')
      print()

    def get_symbol_info(self, symbol):
        # make a GET request to the API to get the current balance of the trading account
        info = self.client.get_symbol_info(symbol=symbol)

        if(info != None):

          Lotsize_minQty = float([i for i in info['filters'] if i['filterType'] == 'LOT_SIZE'][0]['minQty'])

          Lotsize_maxQty = float([i for i in info['filters'] if i['filterType'] == 'LOT_SIZE'][0]['maxQty'])

          Lotsize_stepSize = float([i for i in info['filters'] if i['filterType'] == 'LOT_SIZE'][0]['stepSize'])

        return info

    def get_all_data_from_csv(self, symbol, timeframe, ticks):
        # read the CSV file and get all the data from the last nth ticks
        with open('data/' + timeframe + '/trading_data_' + symbol + '_' + timeframe + '.csv', 'r') as csvfile:
            reader = csv.reader(csvfile)
            data = list(reader)[-ticks:]

        pd_data = pd.read_csv('data/' + timeframe + '/trading_data_' + symbol + '_' + timeframe + '.csv').tail(ticks).values.tolist()

        # convert the data to a DataFrame
        df = pd.DataFrame(pd_data, columns=['event_time', 'symbol', 'start_time', 'end_time', 'open', 'close', 'high', 'low', 'volume', 'number_of_trades', 'quote_volume', 'volume_of_active_buy', 'quote_volume_of_active_buy'])

        df['close'].astype(float)
        df['high'].astype(float)
        df['low'].astype(float)
        df['volume'].astype(float)
        df['number_of_trades'].astype(float)
        df['quote_volume'].astype(float)
        df['volume_of_active_buy'].astype(float)
        df['quote_volume_of_active_buy'].astype(float)

        return df

    def check_balance(self, symbol, quantity, buffer):
        # make a GET request to the API to get the current balance of the trading account
        balance = self.client.get_asset_balance(asset=self.get_asset(symbol))

        # check if enough balance to trade
        if float(balance['free']) > (quantity * buffer):
            return True
        else:
            return False

    def calculate_order_size(self, symbol, investment_percentage):
        # get the current balance of the trading account
        balance = self.client.get_asset_balance(asset=self.get_asset(symbol))

        # get investment amount for investment percentage
        investment = float(balance['free']) * investment_percentage

        return investment

    def calc_price(self, price, risk_factor, profit, step_size):

        # calculate the stop loss and take profit prices with risk factor
        oco_price_low = price * (1 - risk_factor * profit)
        oco_price_high = price * (1 + profit)

        price = round_step_size(price, step_size)
        oco_price_low = round_step_size(oco_price_low, step_size)
        oco_price_high = round_step_size(oco_price_high, step_size)

        return oco_price_low, oco_price_high


    def place_order(self, symbol, side, profit, risk_factor, investment_percentage):

        # close all open orders
        # self.close_all_orders()

        # make a POST request to the API to place an order
        # get the current price of the symbol
        price = float(self.client.get_symbol_ticker(symbol=symbol).get('price'))

        # check if price is valid
        symbol_info = self.get_symbol_info(symbol)
        min_price = float([i for i in symbol_info['filters'] if i['filterType'] == 'PRICE_FILTER'][0]['minPrice'])
        max_price = float([i for i in symbol_info['filters'] if i['filterType'] == 'PRICE_FILTER'][0]['maxPrice'])
        tick_size = float([i for i in symbol_info['filters'] if i['filterType'] == 'PRICE_FILTER'][0]['tickSize'])

        # set price to min or max if it is out of range
        if price < min_price:
            return None
        elif price > max_price:
            return None

        # calculate the stop loss and take profit prices with risk factor
        oco_price_low = price * (1 - risk_factor * profit)
        oco_price_high = price * (1 + profit)

        # round the prices to the nearest tick size
        price = round_step_size(price, tick_size)
        oco_price_low = round_step_size(oco_price_low, tick_size)
        oco_price_high = round_step_size(oco_price_high, tick_size)

        oco_limit_low = round_step_size((oco_price_low + price)/2, tick_size)
        oco_limit_high = round_step_size((oco_price_high + price)/2, tick_size)

        print('##########################################################################################')
        print("Price: ", price, "Stop Loss: ", oco_price_low, "Take Profit: ", oco_price_high)
        print("Limit Stop Loss: ", oco_limit_low, "Limit Take Profit: ", oco_limit_high)
        print("Min Price: ", min_price, "Max Price: ", max_price, "Tick Size: ", tick_size)

        # calculate quantity
        quantity = self.calculate_order_size(symbol, investment_percentage)

        # check if quantity is valid
        min_qty = float([i for i in symbol_info['filters'] if i['filterType'] == 'LOT_SIZE'][0]['minQty'])
        max_qty = float([i for i in symbol_info['filters'] if i['filterType'] == 'LOT_SIZE'][0]['maxQty'])
        step_size = float([i for i in symbol_info['filters'] if i['filterType'] == 'LOT_SIZE'][0]['stepSize'])


        quantity = round_step_size(quantity, step_size)

        # set quantity to minimum if it is less than minimum and maximum if it is more than maximum
        if quantity < min_qty:
            quantity = min_qty
        elif quantity > max_qty:
            quantity = max_qty


        print("Min Quantity: ", min_qty, "Max Quantity: ", max_qty, "Step Size: ", step_size)
        print("Quantity: ", quantity)
        print('##########################################################################################')
        print()

        # check if enough balance to trade
        if self.check_balance(symbol, quantity, 1.1):
            print('##########################################################################################')
            print("Enough balance to trade")
            print('##########################################################################################')
            print()
        else:
            print('##########################################################################################')
            print("Not enough balance to trade")
            print('##########################################################################################')
            print()
            return None

        if side == SIDE_BUY:
          try:
            test_order = self.client.create_test_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_LIMIT,
                quantity=quantity,
                price=str(price),
                timeInForce=TIME_IN_FORCE_GTC
            )
          except Exception as e:
              print("An exception occured - {}".format(e))
              return None
          try:
              order = self.client.create_order(
                  symbol=symbol,
                  side=side,
                  type=ORDER_TYPE_LIMIT,
                  quantity=quantity,
                  price=str(price),
                  timeInForce=TIME_IN_FORCE_GTC
              )
          except Exception as e:
              print("An exception occured - {}".format(e))
              return None
          if order != None:
              try:
                oco_order = self.client.create_oco_order(
                    symbol=symbol,
                    side=SIDE_SELL,
                    quantity=quantity,
                    price=str(oco_price_high),
                    stopPrice=str(oco_price_low),
                    stopLimitPrice=str(oco_price_low),
                    stopLimitTimeInForce=TIME_IN_FORCE_GTC,
                )
              except Exception as e:
                print("An exception occured - {}".format(e))
                return None
        elif side == SIDE_SELL:
          try:
            test_order = self.client.create_test_order(
                  symbol=symbol,
                  side=side,
                  type=ORDER_TYPE_LIMIT,
                  quantity=quantity,
                  price=str(price),
                  timeInForce=TIME_IN_FORCE_GTC
            )
          except Exception as e:
              print("An exception occured - {}".format(e))
              return None
          try:
              order = self.client.create_order(
                  symbol=symbol,
                  side=side,
                  type=ORDER_TYPE_LIMIT,
                  quantity=quantity,
                  price=str(price),
                  timeInForce=TIME_IN_FORCE_GTC
              )
          except Exception as e:
              print("An exception occured - {}".format(e))
              return None
          if order != None:
            try:
              oco_order = self.client.create_oco_order(
                  symbol=symbol,
                  side=SIDE_BUY,
                  quantity=quantity,
                  price=str(oco_price_low),
                  stopPrice=str(oco_price_high),
                  stopLimitPrice=str(oco_price_high),
                  stopLimitTimeInForce=TIME_IN_FORCE_GTC,
              )
            except Exception as e:
                print("An exception occured - {}".format(e))
                return None

        if order != None and oco_order != None:
          with open('data/trading/order_mapping.csv', 'a+') as csvfile:
              writer = csv.writer(csvfile)
              writer.writerow([symbol, order['orderId'], oco_order['orders'][0]['orderId'], oco_order['orders'][1]['orderId']])
          csvfile.close()
        else: 
          self.cancel_failed_orders(symbol, order, oco_order)
          return None

        return [order, oco_order]

    # create a function that listens for data from a websocket and puts it in a CSV file
    def listen_to_websocket(self):
        # define the timeframes
        timeframes = ['1s', '1m']

        # get all symbols from the API
        symbols = self.client.get_all_tickers()

        for symbol in symbols:
          for timeframe in timeframes:
            worker = Thread(target=run_stream, args=(symbol.get('symbol'), timeframe))
            worker.deamon = True
            worker.start()
        

    # create a function that processes data from the queue and makes trading decisions
    def process_data(self, symbol, timeframe, ticks, profit, risk_factor, investment_percentage, trades):

        data_length = 0

        num_of_trades = trades

        while data_length < ticks:
          # get number of rows in the csv file that are valid and from recent responsens
          with open('data/' + timeframe + '/trading_data_' + symbol + '_' + timeframe + '.csv', 'r') as csvfile:
              reader = csv.reader(csvfile)
              data = list(reader)[-ticks:]
              data_length = len(data)

        while num_of_trades > 0:

            # get the data from the csv file
            with open('data/' + timeframe + '/trading_data_' + symbol + '_' + timeframe + '.csv', 'r') as csvfile:
                reader = csv.reader(csvfile)
                data = list(reader)[-ticks:]
            
            all_data = self.get_all_data_from_csv(symbol, timeframe, ticks)['close'].astype(float)

            # get macd sentiment
            macd = macd_strategy(all_data)
            macd_signal = macd['Signal'].iloc[-1]
            print('##########################################################################################')
            print("MACD-Signal:", macd_signal, "MACD:", macd['MACD'].iloc[-1])

            # calculate the RSI
            rsi = calculate_rsi(all_data)
            rsi_signal = "HOLD"
            if rsi.iloc[-1] > 60:
                rsi_signal = Client.SIDE_SELL
            elif rsi.iloc[-1] < 40:
              rsi_signal = Client.SIDE_BUY
            print("RSI-Signal:", rsi_signal, "RSI:", rsi.iloc[-1])

            # decide on an order
            
            side = decide_on_order(rsi_signal, macd_signal)
            print("Order Side:", side)
            print('##########################################################################################')
            print()


            # get the current price
            price = self.client.get_symbol_ticker(symbol=symbol)['price']

            # create folder if it does not exist
            os.makedirs('data/indicators/' + timeframe, exist_ok=True)
            
            # save price, side, rsi and macd to csv file
            with open('data/indicators/' + timeframe + '/indicator_data_' + symbol + '_' + timeframe + '.csv', 'a+') as csvfile:
              writer = csv.writer(csvfile)

              # Read all rows of the CSV file into a list
              #csvfile.seek(0)
              #rows = list(csv.reader(csvfile))

              # Get the last row
              #last_row = rows[-1] if rows else None

              #if last_row is None or str(rsi.iloc[-1]) != last_row[2]:
              writer.writerow([price, side, rsi.iloc[-1], macd['MACD'].iloc[-1]])

            if side != None:
              # execute the decision
              order =  self.place_order(symbol, side, profit, risk_factor, investment_percentage)
              if order != None:
                num_of_trades -= 1
                print('##########################################################################################')
                print("Order ID:", order[0]['orderId'], "Number of trades left:", num_of_trades)
                print('##########################################################################################')
                print()
              else:
                print('##########################################################################################')
                print("Order not placed")
                print('##########################################################################################')
                print()
            # wait for the next tick
            time.sleep(self.tickrate(timeframe))
          
        print('##########################################################################################')
        print("###################################  Trading finished  ###################################")
        print('##########################################################################################')
        print()

    def cancel_failed_orders(self, order, order_oco):
        if order == None:
          self.client.cancel_order(symbol=order_oco['symbol'], orderId=order_oco['orderId'])
        if order_oco == None:
          self.client.cancel_order(symbol=order['symbol'], orderId=order['orderId'])

    def cancel_order(self, symbol, order_id):
      if symbol == "":
        all_orders = self.client.get_all_orders(symbol, orderId=order_id)
        for order in all_orders:
          try:
            self.client.cancel_order(symbol=symbol, orderId=order_id)
          except:
            return False
      try:
        self.client.cancel_order(symbol=symbol, orderId=order_id)
      except:
        return False
      return True

    def get_open_orders(self):
        # get every open orders from orders.csv
        open_orders = self.client.get_open_orders()

        return open_orders

    def get_all_orders(self):
        # get every open orders from orders.csv
        tickers = self.client.get_all_tickers()
        symbols = []

        for symbol in tickers:
            print(symbol['symbol'])
            symbols.append(symbol['symbol'])

        while True:
          symbol = input("Select for which symbol you want to see the orders: ")
          if symbol in symbols:
              all_orders = self.client.get_all_orders(symbol=symbol)
              break
          else:
              print("Symbol not found!")
              continue

        return all_orders

    def tickrate(self, timeframe):
          if timeframe == "1s":
            return 1
          elif timeframe == "3s":
            return 3
          elif timeframe == "5s":
            return 5
          elif timeframe == "15s":
            return 15
          elif timeframe == "30s":
            return 30
          elif timeframe == "1m":
            return 60
          elif timeframe == "3m":
            return 180
          elif timeframe == "5m":
            return 300
          elif timeframe == "15m":
            return 900
          elif timeframe == "30m":
            return 1800
          elif timeframe == "1h":
            return 3600
          elif timeframe == "2h":
            return 7200
          elif timeframe == "4h":
            return 14400
          elif timeframe == "6h":
            return 21600
          elif timeframe == "8h":
            return 28800
          elif timeframe == "12h":
            return 43200
          elif timeframe == "1d":
            return 86400
          elif timeframe == "3d":
            return 259200
          elif timeframe == "1w":
            return 604800
          elif timeframe == "1M":
            return 2592000