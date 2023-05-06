import pandas as pd
import numpy as np
import config
from datetime import datetime, timedelta,date
from xAPIConnector import *
from dateutil.relativedelta import *

user_id = config.user_id
pwd= config.pwd




class DataCollectorXtb():
    
    ''' Class for collection historical data from XTB using API 
    
    Attrs
    ==================
    
    symbol - string
            ticker symbol e.g 'EURUSD'
    
    start - string
            start date
    
    end - string
          end date
    
    period - string
           period in format e.g. '5min' - 5 minutes, '1h' - 1 hour
    
    cols_to_save - list
                list of columns to save, possible items ['Open', 'Close', 'High', 'Low', 'vol']
    
    
    
    spread_col - boolean
                add column with spreads
    
    '''
    def __init__(self, symbol, start, end, period, cols_to_save=['Open', 'Close', 'High', 'Low', 'vol'],
                 spread_col=False):
        
        self.symbol = symbol
        self.start = start
        self.end = end
        self.cols_to_save = cols_to_save
        self.data = None
        self.period_dict = {'1min': 1, '5min': 5, '15min': 15, '30min': 30, '1h': 60, '4h': 240, '1D': 1440}
        self.max_range = {'1min': 1, '5min': 1, '15min': 1, '30min': 6, '1h': 6, '4h': 12}
        self.period = period
        self.spread_col=spread_col
        self.check_max_range()
        self.get_data()

    def __repr__(self):
        rep = "DataCollector(symbol = {}, start = {}, end = {}, period= {})"
        return rep.format(self.symbol, self.start, self.end, self.period)

    def check_max_range(self):
        
        '''Check max range for given period and correct it if exceeded'''
        
        if self.period in self.max_range.keys():

            end = datetime.now()
            start = datetime.strptime(self.start, '%Y-%m-%d')
            delta = relativedelta(end, start)

            delta_months = delta.months + (delta.years * 12)

            if self.max_range[self.period] < delta_months:
                print(f"Max range for given period {self.period} is {self.max_range[self.period]} months from now")
                date_start = datetime.now() + relativedelta(months=-self.max_range[self.period])
                if date_start > datetime.strptime(self.end, '%Y-%m-%d'):
                    self.end = datetime.now().strftime('%Y-%m-%d')
                    print(f"End date is set to {self.end}")
                

                self.start = date_start.strftime('%Y-%m-%d')
                print(f"Start date is set to {self.start}")
    
    def history_converter(self, history):
        
        '''Convert data from dict to pandas df'''
        
        df_dict = history['returnData']['rateInfos']
        digits = history['returnData']['digits']

        df = pd.DataFrame.from_dict(df_dict)

        df['Date'] = df['ctm'].apply(lambda x: datetime.fromtimestamp(x / 1000))
        df['Open'] = df['open'] / (10 ** digits)
        df['Close'] = df['Open'] + df['close'] / (10 ** digits)
        df['High'] = df['Open'] + df['high'] / (10 ** digits)
        df['Low'] = df['Open'] + df['low'] / (10 ** digits)

        df.set_index("Date", inplace=True, drop=True)
        
            
        df = df[self.cols_to_save]

        return df
    def add_spreads(self,df):
        
        '''Add columns with spreads and pips to df '''
        
        spreads=pd.read_csv(f'{config.spread_folder}{self.symbol}_spreads.csv', parse_dates=['date'], index_col='date')
        df['weekday']=df.index.day_name()
        df['hour']=df.index.hour
        df=df[df['weekday']!='Sunday']
        m_df=pd.merge(df.reset_index(), spreads, how='left',on=['weekday','hour']).set_index('Date').fillna(method='ffill')
        m_df=m_df.drop(['weekday','hour'], axis=1)
        return m_df
        
    def get_data(self):
        
        ''' Collect and prepares the data'''
    
        filename=''
        end_date = datetime.strptime(self.end, '%Y-%m-%d')
        end = int(datetime.timestamp(end_date) * 1000)
        start_date = datetime.strptime(self.start, '%Y-%m-%d')
        start = int(datetime.timestamp(start_date) * 1000)
        args = {'info': {
            'end': end,
            'start': start,
            'symbol': self.symbol,
            'period': self.period_dict[self.period]
        }}
        client = APIClient()
        client.execute(loginCommand(user_id, pwd))
        history_data = client.commandExecute('getChartRangeRequest', arguments=args)
        df = self.history_converter(history_data)


        if self.cols_to_save==['Close'] or self.cols_to_save==['Close','vol']:
            df=df.rename(columns={'Close':self.symbol})


        
        if self.spread_col:
            df=self.add_spreads(df)
            

        self.data = df


