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
      filename = 'data/trading/order_mapping.csv'

      df = pd.read_csv(filename, header=None)
      order_mapping = df.values.tolist()
      

      print(order_mapping)
      orders = []
      symbol = ""
      
      # ite3rate through orders and check status
      for order in order_mapping:
        if order != []:
          symbol = order[0]

          print(order)

          order_orig = self.client.get_order(symbol=symbol, orderId=int(order[1]))
          oco_order_low = self.client.get_order(symbol=symbol, orderId=int(order[2]))
          oco_order_high = self.client.get_order(symbol=symbol, orderId=int(order[3]))

          new_order = [order_orig['orderId'], order_orig['status'], order_orig['origQty'], order_orig['price'], order_orig['side'], oco_order_low['orderId'], oco_order_low['status'], oco_order_high['orderId'], oco_order_high['status']]
          
          filename = 'data/trading/orders_' + symbol + '.csv'

          df = pd.DataFrame([new_order])
          df.to_csv(filename, mode='a', header=False, index=False)

      print('##########################################################################################')
      print("##################################  Orders tracked  ######################################")
      print('##########################################################################################')
      print()

    def track_profit(self, symbol):
      filename = 'data/trading/orders_' + symbol + '.csv'

      df = pd.read_csv(filename, header=None)
      orders = df.values.tolist()
      num_of_orders = len(orders)

      profit_sum = 0
      messages = []

      filename = 'data/trading/profit_' + symbol + '.csv'
      pd.DataFrame().to_csv(filename, mode='w+', index=False)

        # iterate through orders and check status
      while num_of_orders > 0:
        for order in orders:
          if order != []:

            message = ''
            profit = 0

            order_orig = self.client.get_order(symbol=symbol, orderId=order[0])
            oco_order_low = self.client.get_order(symbol=symbol, orderId=order[5])
            oco_order_high = self.client.get_order(symbol=symbol, orderId=order[7])

            if order_orig['status'] == 'FILLED' and order_orig['side'] == 'BUY':
              if oco_order_low['status'] == 'FILLED':
                profit = float(oco_order_low['cummulativeQuoteQty']) - float(order_orig['cummulativeQuoteQty'])
                message = "Loss: " + str(profit) + " trading " + symbol + " on " + order_orig['side'] + " with " + order_orig['price'] + " sold at " + oco_order_low['price']
                num_of_orders -= 1
              elif oco_order_high['status'] == 'FILLED':
                profit = float(oco_order_high['cummulativeQuoteQty']) - float(order_orig['cummulativeQuoteQty'])
                message = "Profit: " + str(profit) + " trading " + symbol + " on " + order_orig['side'] + " with " + order_orig['price'] + " sold at " + oco_order_high['price']
                num_of_orders -= 1
            elif order_orig['status'] == 'FILLED' and order_orig['side'] == 'SELL':
              if oco_order_low['status'] == 'FILLED':
                profit = float(order_orig['cummulativeQuoteQty']) - float(oco_order_low['cummulativeQuoteQty'])
                message = "Loss: " + str(profit) + " trading " + symbol + " on " + order_orig['side'] + " with " + order_orig['price'] + " bought at " + oco_order_low['price']
                num_of_orders -= 1
              elif oco_order_high['status'] == 'FILLED':
                profit = float(order_orig['cummulativeQuoteQty']) - float(oco_order_high['cummulativeQuoteQty'])
                message = "Profit: " + str(profit) + " trading " + symbol + " on " + order_orig['side'] + " with " + order_orig['price'] + " bought at " + oco_order_high['price']
                num_of_orders -= 1

            print("message: " + message)
            print("profit: " + str(profit))

            if message == '':
              continue

            if profit == 0:
              continue

            # append order to profit history
            filename = 'data/trading/profit_history_' + symbol + '.csv'

            df = pd.DataFrame([[message]], columns=['message'])
            df.to_csv(filename, mode='a', header=False, index=False)


            filename = 'data/trading/profit_' + symbol + '.csv'
            # append the new profit to the file
            df = pd.DataFrame([profit])
            df.to_csv(filename, mode='a+', header=False, index=False)

            # read the current cumulative profit from file
            df = pd.read_csv(filename, header=None)
            cumulative_profit = df.sum()

            profit_sum = cumulative_profit

              
            if num_of_orders == 0:
              break
            else :
              continue

      print('##########################################################################################') 
      print("Profit: " + str(profit_sum))
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
        filename = 'data/' + timeframe + '/trading_data_' + symbol + '_' + timeframe + '.csv'
        
        df = pd.read_csv(filename, names=['type', 'symbol', 'start_time', 'end_time', 'open', 'close', 'high', 'low', 'volume', 'number_of_trades', 'quote_volume', 'volume_of_active_buy', 'quote_volume_of_active_buy']).tail(ticks)

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
          filename = 'data/trading/order_mapping.csv'

          df = pd.DataFrame([[symbol, order['orderId'], oco_order['orders'][0]['orderId'], oco_order['orders'][1]['orderId']]], columns=['symbol', 'orderId', 'oco_order_1', 'oco_order_2'])
          df.to_csv(filename, mode='a', header=False, index=False)
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
          filename = 'data/' + timeframe + '/trading_data_' + symbol + '_' + timeframe + '.csv'
          df = pd.read_csv(filename)
          data = df.tail(ticks)
          data_length = len(data)

        while num_of_trades > 0:

            # get all data from the csv file
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
            filename = 'data/indicators/' + timeframe + '/indicator_data_' + symbol + '_' + timeframe + '.csv'
            df = pd.DataFrame([[price, side, rsi.iloc[-1], macd['MACD'].iloc[-1]]], columns=['price', 'side', 'rsi', 'macd'])
            df.to_csv(filename, mode='a', header=False, index=False)

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