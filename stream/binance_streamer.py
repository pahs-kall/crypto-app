import websocket
import stream.csv_handler as csv_handler

def on_message(ws, message):
    #print()
    #print(str(datetime.datetime.now()) + ": ")
    #db.log_db(message)
    csv_handler.log_csv(message)

def on_error(ws, error):
    print(error) 

def on_close(ws, close_status_code, close_msg):
    print("### closed ###" + close_msg)


def streamKline(symbol, interval):
    websocket.enableTrace(False)
    socket = f'wss://stream.binance.com:9443/ws/{symbol.lower()}@kline_{interval}'
    ws = websocket.WebSocketApp(socket,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever()

def run_stream(symbol, interval):
    #print("symbol: " + symbol + " interval: " + interval)
    streamKline(symbol, interval)
