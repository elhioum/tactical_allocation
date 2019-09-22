# -*- coding: utf-8 -*-
"""
Mohamed El Hioum

This simulator package
"""

import bt
import pandas as pd
from datetime import date

class WeighTarget(bt.Algo):
    """
    Sets target weights based on a target weight DataFrame.

    Args:
        * target_weights (DataFrame): DataFrame containing the target weights

    Sets:
        * weights

    """

    def __init__(self, target_weights):
        self.tw = target_weights

    def __call__(self, target):
        # get target weights on date target.now
        if target.now in self.tw.index:
            w = self.tw.loc[target.now]

            # save in temp - this will be used by the weighing algo
            # also dropping any na's just in case they pop up
            target.temp['weights'] = w.dropna()

        # return True because we want to keep on moving down the stack
        return True
    
class SelectWhere(bt.Algo):

    """
    Selects securities based on an indicator DataFrame.

    Selects securities where the value is True on the current date (target.now).

    Args:
        * signal (DataFrame): DataFrame containing the signal (boolean DataFrame)

    Sets:
        * selected

    """
    def __init__(self, signal):
        self.signal = signal

    def __call__(self, target):
        # get signal on target.now
        if target.now in self.signal.index:
            sig = (self.signal.loc[target.now]==True)

            # get indices where true as list
            selected = list(sig.index[sig])

            # save in temp - this will be used by the weighing algo
            target.temp['selected'] = selected

        # return True because we want to keep on moving down the stack
        return True



class RealisticStrategies():
    underlyings=[]
    startDate=date.today()
    rebalFreq = 20
    endDate = date.today()
    strat = []
    
    def __init__ (self, OppSet, RebalFreqDays, StartDate, EndDate=date.today()):
        self.underlyings = OppSet
        self.rebalFreq = RebalFreqDays
        self.startDate = StartDate
        self.endDate = EndDate
    
    def generateSignals(self, data):
        returns = data.pct_change(periods=self.rebalFreq)
        returns['Mid']=returns.quantile(.5,axis=1)
        sig = data.copy()
        
        for tkr in map(lambda x: x.lower(), self.underlyings):
            sig[tkr] = (returns[tkr]>=returns['Mid'])
        sig.fillna(False)
        self.trendSignal = sig.copy()
        sig2 = sig.copy()
        for tkr in map(lambda x: x.lower(), self.underlyings):
            sig2[tkr] = (returns[tkr]<=returns['Mid'])
        sig2.fillna(False)
        self.revSignal = sig2.copy()
        
        self.utrendSignal = self.trendSignal.shift(periods=-self.rebalFreq)
        self.utrendSignal.fillna(False)
        self.trendSignal = self.trendSignal.shift(periods=5)
        self.trendSignal.fillna(False)
    
    def generateStrategies(self): 
        self.strat.append(bt.Strategy('InvVol',[bt.algos.RunQuarterly(),
                                        bt.algos.SelectAll(),
                                        bt.algos.WeighInvVol(),
                                        bt.algos.Rebalance()
                                        ]))
        
        self.strat.append(bt.Strategy('Trend',[SelectWhere(self.trendSignal),
                                        bt.algos.RunQuarterly(),
                                        bt.algos.WeighInvVol(),
                                        bt.algos.Rebalance()
                                        ]))
        self.strat.append(bt.Strategy('Reversal',[SelectWhere(self.revSignal),
                                        bt.algos.RunQuarterly(),
                                        bt.algos.WeighInvVol(),
                                        bt.algos.Rebalance()
                                        ]))
         
        self.strat.append(bt.Strategy('BestCase',[SelectWhere(self.utrendSignal),
                                        bt.algos.RunQuarterly(),
                                        bt.algos.WeighInvVol(),
                                        bt.algos.Rebalance()
                                        ]))
       
    def run(self):
        data = bt.get(self.underlyings,start=self.startDate)
        self.data = data
        # Run Signals
        self.generateSignals(data)
        self.generateStrategies()
        test = []
        res = []
        #Generate Strategies
        for s in self.strat:
            test=bt.Backtest(s,data[data.index < self.endDate])
            res.append(bt.run(test))
            
        return res
    
        
# Define the instruments to download. We would like to see Sector ETFs.
tickers = ['VLUE','QUAL','MTUM','SIZE','USMV']

d1 = '2000-01-01'
d2 = '2019-06-30'

real = RealisticStrategies(tickers,60,d1,d2) # Quarterly
result = real.run()
timeseries = result[0]._get_series('1D').copy()
for res in result:
    for k in res.keys():
        timeseries[k]=res._get_series('1D')
relresult = {}        
s={}
lst = ['Trend','Reversal','BestCase']
for l in lst:
    tw=timeseries.copy()*0
    tw['InvVol']=-1
    tw[l]=1
    s[l]=bt.Strategy(l+'Relative',[WeighTarget(tw),
                                  bt.algos.RunQuarterly(),
                                  bt.algos.Rebalance()])
    test=bt.Backtest(s[l],timeseries)
    relresult[l]=bt.run(test)

reltimeseries = timeseries.copy()

for strtgy in relresult.keys():
    for k in relresult[strtgy].keys():
        reltimeseries[k]=relresult[strtgy]._get_series('1D')

reltimeseries.to_csv('Factors'+d1+'.csv')    
reltimeseries = reltimeseries.drop(['Trend','Reversal','BestCase','InvVol'],axis=1)

    