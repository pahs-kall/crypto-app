from trading_algo import TradingBot
from multiprocessing import Process
from secret import TEST_API_KEY, TEST_SECRET_KEY

bot = TradingBot(TEST_API_KEY, TEST_SECRET_KEY)
 
open_orders = bot.client.get_open_orders()

for order in open_orders:
  bot.client.cancel_order(symbol=order['symbol'], orderId=order['orderId'])
