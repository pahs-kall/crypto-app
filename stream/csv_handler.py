import json
import csv
import os
import pandas as pd

def log_csv(message):
        data = json.loads(message)

        k = data["k"]

        symbol = k["s"]
        interval = k["i"]

        if not os.path.exists('data/' + interval):
            os.makedirs('data/' + interval)

        filename = 'data/' + interval + '/trading_data_' + symbol + '_' + interval + '.csv'
        df = pd.DataFrame([[
            data['E'], # type
            data['s'], # symbol
            data['k']['t'], # start time of bar
            data['k']['T'], # end time of bar
            data['k']['o'], # open
            data['k']['c'], # close
            data['k']['h'], # high
            data['k']['l'], # low
            data['k']['v'], # volume
            data['k']['n'], # number of trades
            data['k']['q'], # quote volume
            data['k']['V'], # volume of active buy
            data['k']['Q']  # quote volume of active buy
        ]], columns=['type', 'symbol', 'start_time', 'end_time', 'open', 'close', 'high', 'low', 'volume', 'number_of_trades', 'quote_volume', 'volume_of_active_buy', 'quote_volume_of_active_buy'])
        df.to_csv(filename, mode='a', header=False, index=False)



        