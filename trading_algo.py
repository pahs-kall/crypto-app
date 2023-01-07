import json
from constants import *
from strategies.macd import macd_strategy
from strategies.rsi import calculate_rsi, decide_on_order
from binance.client import Client
from binance.enums import *
from stream.binance_streamer import run_stream
import csv
import os
import time
import pandas as pd
import websocket
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

        return exchange_info

    def get_asset(self, pair):
        # get exchange info
        exchange_info = self.client.get_exchange_info()
        for symbol in exchange_info.get('symbols'):
            if symbol.get('symbol') == pair:
                return symbol.get('baseAsset')

    def check_order(self, symbol, order_id):
        order = self.client.get_order(symbol=symbol, orderId=order_id)

        return order

    def calculate_order_size(self, symbol, investment_percentage):
        # get the current balance of the trading account
        balance = self.client.get_asset_balance(asset=self.get_asset(symbol))

        # get investment amount for investment percentage
        investment = float(balance['free']) * investment_percentage

        print("asset: ", self.get_asset(symbol))

        # get the current price of the symbol
        price = self.client.get_symbol_ticker(symbol=symbol)

        # calculate the order size for investment for take profit price
        order_size = investment / float(price['price'])

        return order_size

    def track_trades(self):
        # check if orders on orders.csv are filled
        with open('data/orders.csv', 'r') as csvfile:
            reader = csv.reader(csvfile)
            orders = list(reader)


        print(orders)

        # get sl and tp orders for each filled order
        for order in orders:
          while order != []:
            if order[4] == 'FILLED':
              order_orig = self.check_order(order[1])
              order_sl = self.check_order(order[0], order[6])
              order_tp = self.check_order(order[0], order[7])
              # update order in orders.csv if sl or tp is filled
              if order_sl['status'] == 'FILLED' or order_tp['status'] == 'FILLED':
                orders.remove(order)
                order[4] = 'CLOSED'
                orders.append(order)
                # write updated orders.csv
                with open('data/orders.csv', 'w') as csvfile:
                  writer = csv.writer(csvfile)
                  writer.writerows(orders)
              # close non filled sl and tp orders
              if order_sl['status'] == 'FILLED':
                self.client.cancel_order(symbol=order[0], orderId=order[6])
              elif order_tp['status'] == 'NEW':
                self.client.cancel_order(symbol=order[0], orderId=order[7])

              # track profit
              if order_sl['status'] == 'FILLED':
                loss = float(order_sl['price']) - float(order_orig[4]) * float(order_orig[5])
                print("Loss: ", loss, "OrderId: ", order[0])
                # save loss to profti.csv
                with open('data/profit.csv', 'a') as csvfile:
                  writer = csv.writer(csvfile)
                  writer.writerow([loss])
              elif order_tp['status'] == 'FILLED':
                profit = float(order_tp['price']) - float(order[4]) * float(order[5])
                print("Profit: ", profit, "OrderId: ", order[0])
                # save profit to profti.csv
                with open('data/profit.csv', 'a') as csvfile:
                  writer = csv.writer(csvfile)
                  writer.writerow([profit])

        
        # update orders.csv
        for order in orders:
          while order != []:
            new_order = self.check_order(order[0], order[1])
            # update order status
            order[6] = new_order['status']
            # update order filled quantity
            if order[6] == 'FILLED':
              order_sl = self.check_order(order[0], order[9])
              order_tp = self.check_order(order[0], order[10])
              if order_sl['status'] == 'FILLED':
                self.client.cancel_order(symbol=order[0], orderId=order[9])
                # remove order from orders.csv
                orders.remove(order)
              elif order_tp['status'] == 'FILLED':
                self.client.cancel_order(symbol=order[0], orderId=order[10])
                # remove order from orders.csv
                orders.remove(order)
          
          # write updated orders.csv
          with open('data/orders.csv', 'w') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(orders)

        
    def get_symbol_info(self, symbol):
        # make a GET request to the API to get the current balance of the trading account
        info = self.client.get_symbol_info(symbol=symbol)

        if(info != None):

          Lotsize_minQty = float([i for i in info['filters'] if i['filterType'] == 'LOT_SIZE'][0]['minQty'])

          Lotsize_maxQty = float([i for i in info['filters'] if i['filterType'] == 'LOT_SIZE'][0]['maxQty'])

          Lotsize_stepSize = float([i for i in info['filters'] if i['filterType'] == 'LOT_SIZE'][0]['stepSize'])

          print("Minimum Quantity: ", Lotsize_minQty)
          print("Maximum Quantity: ", Lotsize_maxQty)
          print("Maximum Stepzie: ", Lotsize_stepSize)

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

    def get_open_orders(self):
        # get every open orders from orders.csv
        open_orders = self.client.get_open_orders()

        return open_orders

    def close_all_orders(self):
        # get every open orders from orders.csv
        open_orders = self.client.get_open_orders()

        # close all open orders
        for order in open_orders:
            self.client.cancel_order(symbol=order['symbol'], orderId=order['orderId'])

    def check_balance(self, symbol, price, quantity, buffer):
        # make a GET request to the API to get the current balance of the trading account
        balance = self.client.get_asset_balance(asset=self.get_asset(symbol))

        # check if enough balance to trade
        if float(balance['free']) > (price * quantity * buffer):
            return True
        else:
            return False

    def calc_price(self, price, risk_factor, profit, step_size):

        # calculate the stop loss and take profit prices with risk factor
        stop_loss = price * (1 - risk_factor * profit)
        take_profit = price * (1 + profit)

        price = round_step_size(price, step_size)
        stop_loss = round_step_size(stop_loss, step_size)
        take_profit = round_step_size(take_profit, step_size)

        return stop_loss, take_profit


    def place_order(self, symbol, side, profit, risk_factor, investment_percentage):

        # close all open orders
        # self.close_all_orders()

        # make a POST request to the API to place an order
        # get the current price of the symbol
        price = float(self.client.get_symbol_ticker(symbol=symbol).get('price'))
        print(price)

        # check if price is valid
        symbol_info = self.get_symbol_info(symbol)
        min_price = float([i for i in symbol_info['filters'] if i['filterType'] == 'PRICE_FILTER'][0]['minPrice'])
        max_price = float([i for i in symbol_info['filters'] if i['filterType'] == 'PRICE_FILTER'][0]['maxPrice'])
        tick_size = float([i for i in symbol_info['filters'] if i['filterType'] == 'PRICE_FILTER'][0]['tickSize'])

        # set price to min or max if it is out of range
        if price < min_price:
            price = min_price
        elif price > max_price:
            price = max_price

        # calculate the stop loss and take profit prices with risk factor
        stop_loss = price * (1 - risk_factor * profit)
        take_profit = price * (1 + profit)

        # round the prices to the nearest tick size
        price = round_step_size(price, tick_size)
        stop_loss = round_step_size(stop_loss, tick_size)
        take_profit = round_step_size(take_profit, tick_size)

        print("Price: ", price, "Stop Loss: ", stop_loss, "Take Profit: ", take_profit)
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

        # check if enough balance to trade
        if self.check_balance(symbol, price, quantity, 1.1):
            print("Enough balance to trade")
        else:
            print("Not enough balance to trade")
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
                self.close_all_orders()
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
                stop_loss, take_profit = self.calc_price(float(order['price']), risk_factor, profit, step_size)
            except Exception as e:
                self.close_all_orders()
                print("An exception occured - {}".format(e))
                return None
            
            if order != None:
              try:
                test_order_sl = self.client.create_test_order(
                    symbol=symbol,
                    side=SIDE_SELL,
                    type=ORDER_TYPE_LIMIT,
                    quantity=quantity,
                    price=str(stop_loss),
                    timeInForce=TIME_IN_FORCE_GTC
                )
              except Exception as e:
                self.close_all_orders()
                print("An exception occured - {}".format(e))
                return None
              try:
                  order_sl = self.client.create_order(
                      symbol=symbol,
                      side=SIDE_SELL,
                      type=ORDER_TYPE_LIMIT,
                      quantity=quantity,
                      price=str(stop_loss),
                      timeInForce=TIME_IN_FORCE_GTC
                  )
              except Exception as e:
                  self.close_all_orders()
                  print("An exception occured - {}".format(e))
                  return None
              try:
                test_order_tp = self.client.create_test_order(
                    symbol=symbol,
                    side=SIDE_SELL,
                    type=ORDER_TYPE_LIMIT,
                    quantity=quantity,
                    price=str(take_profit),
                    timeInForce=TIME_IN_FORCE_GTC
                )
              except Exception as e:
                self.close_all_orders()
                print("An exception occured - {}".format(e))
                return None
              try:
                  order_tp = self.client.create_order(
                      symbol=symbol,
                      side=SIDE_SELL,
                      type=ORDER_TYPE_LIMIT,
                      quantity=quantity,
                      price=str(take_profit),
                      timeInForce=TIME_IN_FORCE_GTC
                  )
              except Exception as e:
                self.close_all_orders()
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
              self.close_all_orders()
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
              self.close_all_orders()
              print("An exception occured - {}".format(e))
              return None

          if order != None:
            try:
              test_order_sl = self.client.create_test_order(
                  symbol=symbol,
                  side=SIDE_BUY,
                  type=ORDER_TYPE_LIMIT,
                  quantity=quantity,
                  price=str(stop_loss),
                  timeInForce=TIME_IN_FORCE_GTC
              )
            except Exception as e:
                self.close_all_orders()
                print("An exception occured - {}".format(e))
                return None
            try:
                order_sl = self.client.create_order(
                    symbol=symbol,
                    side=SIDE_BUY,
                    type=ORDER_TYPE_LIMIT,
                    quantity=quantity,
                    price=str(stop_loss),
                    timeInForce=TIME_IN_FORCE_GTC
                )
            except Exception as e:
                self.close_all_orders()
                print("An exception occured - {}".format(e))
                return None
            try:
              test_order_tp = self.client.create_test_order(
                  symbol=symbol,
                  side=SIDE_BUY,
                  type=ORDER_TYPE_LIMIT,
                  quantity=quantity,
                  price=str(take_profit),
                  timeInForce=TIME_IN_FORCE_GTC
              )
            except Exception as e:
                self.close_all_orders()
                print("An exception occured - {}".format(e))
                return None
            try:
                order_tp = self.client.create_order(
                    symbol=symbol,
                    side=SIDE_BUY,
                    type=ORDER_TYPE_LIMIT,
                    quantity=quantity,
                    price=str(take_profit),
                    timeInForce=TIME_IN_FORCE_GTC
                )
            except Exception as e:
                self.close_all_orders()
                print("An exception occured - {}".format(e))
                return None

        # write order to csv file
        with open('data/orders.csv', 'a') as csvfile:
            writer = csv.writer(csvfile)
            print(order)
            writer.writerow([order['symbol'], order['orderId'], order['price'], order['side'], order['status'], order['transactTime'], order_sl['orderId'], order_tp['orderId']])
        # write sl_order to csv file
        with open('data/sl_orders.csv', 'a') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([order_sl['symbol'], order_sl['orderId'], order_sl['price'], order_sl['side'], order_sl['status'], order_sl['transactTime'], order['orderId']]) 
        # write tp_order to csv file
        with open('data/tp_orders.csv', 'a') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([order_tp['symbol'], order_tp['orderId'], order_tp['price'], order_tp['side'], order_tp['status'], order_tp['transactTime'], order['orderId']])

        return order

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
  
          
    def track_profit(self):

        profit = 0

        while True:
          self.track_trades()

          # calculate profit from profit.csv
          with open('data/profit.csv', 'r') as csvfile:
              reader = csv.reader(csvfile)
              for row in reader:
                  profit += float(row[1])
              
              print("Profit: " + str(profit))
        
          time.sleep(1)
        

    # create a function that processes data from the queue and makes trading decisions
    def process_data(self, symbol, timeframe, ticks, profit, risk_factor, investment_percentage):

        data_length = 0

        while data_length < ticks:
          # get number of rows in the csv file that are valid and from recent responsens
          with open('data/' + timeframe + '/trading_data_' + symbol + '_' + timeframe + '.csv', 'r') as csvfile:
              reader = csv.reader(csvfile)
              data = list(reader)[-ticks:]
              data_length = len(data)

        while True:
            # get the data from the csv file
            with open('data/' + timeframe + '/trading_data_' + symbol + '_' + timeframe + '.csv', 'r') as csvfile:
                reader = csv.reader(csvfile)
                data = list(reader)[-ticks:]
            
            all_data = self.get_all_data_from_csv(symbol, timeframe, ticks)['close'].astype(float)

            # get macd sentiment
            macd = macd_strategy(all_data)
            macd_signal = macd['Signal'].iloc[-1]
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
                print('##########################################################################################')
                print("Order:", order)
                print("Order ID:", order['orderId'])
                print('##########################################################################################')
              else:
                print('##########################################################################################')
                print("Order not placed")
                print('##########################################################################################')

            # wait for the next tick
            time.sleep(self.tickrate(timeframe))

        


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

    def timeframe(self, tickrate):
          if tickrate == 1:
            return "1s"
          elif tickrate == 3:
            return "3s"
          elif tickrate == 5:
            return "5s"
          elif tickrate == 15:
            return "15s"
          elif tickrate == 30:
            return "30s"
          elif tickrate == 60:
            return "1m"
          elif tickrate == 180:
            return "3m"
          elif tickrate == 300:
            return "5m"
          elif tickrate == 900:
            return "15m"
          elif tickrate == 1800:
            return "30m"
          elif tickrate == 3600:
            return "1h"
          elif tickrate == 7200:
            return "2h"
          elif tickrate == 14400:
            return "4h"
          elif tickrate == 21600:
            return "6h"
          elif tickrate == 28800:
            return "8h"
          elif tickrate == 43200:
            return "12h"
          elif tickrate == 86400:
            return "1d"
          elif tickrate == 259200:
            return "3d"
          elif tickrate == 604800:
            return "1w"
          elif tickrate == 2592000:
            return "1M"


    