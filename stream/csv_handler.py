import json
import csv
import os

def log_csv(message):
        data = json.loads(message)

        k = data["k"]

        symbol = k["s"]
        interval = k["i"]

        if not os.path.exists('data/' + interval):
            os.makedirs('data/' + interval)

        with open('data/' + interval + '/trading_data_' + symbol + '_' + interval + '.csv', 'a') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
              data['E'], # event time
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
              data['k']['Q'] # quote volume of active buy
            ])
 
        csvfile.close()   