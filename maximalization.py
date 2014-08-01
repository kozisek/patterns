#! /usr/bin/env python3

from scipy.optimize import *
import numpy as np
from database import *

def v_index(bid, cost_expected=9000, market_margin=0.1, private_value=-100, passed=True, restriction=0.5, z_index=0, risk_assessment=0.7):
    """
    Second level research. Based on an idea that one can participate in an auction if and only if he knows his highest (lowest in this case) bid. Decides what bid is an ideal combination between high and safe return.
    Overall viability index -  a combination of financial and existencial indices.
    """
    cost_private = cost_expected-private_value
    pvalue = bid-cost_private # private value
    pvalue_expected = cost_private*(market_margin)
    f_index = (pvalue/pvalue_expected)
    mvalue = bid - cost_expected
    mvalue_expected = cost_expected*market_margin
    bid_index = ((mvalue_expected-mvalue)/mvalue)
    e_index = restriction*(1-z_index)*passed+bid_index
    # punishment for being higher than market price and bonus for being lower
    return ((f_index*risk_assessment)+(e_index*(1-risk_assessment)))
#print(v_index(9501))

#res = minimize(v_index, [0,1000000], method='nelder-mead',options={'xtol': 1e-8, 'disp': True})
#ranges = slice(9001, 99999)
#res = optimize.brute(v_index, (ranges,), finish=None)
#print("maximize: "+str(res))

def rebid(bid, failed_bid, last_bid, participants=10, time_remaining=10, time_total=20, cost_expected=9000, market_margin=0.1, private_value=10000, passed=True, restriction=0.5, z_index=0, risk_assessment=0.5):
    # first, sleep for a second - it takes time to make a decision
    # index of chance of success: based on the interval of the last bid and break-even
    # index of financial viability: based on the previous interval, but dependent on the size of the procurement (the larger procurement, the closer we can get to break-even)
    time_ratio = time_remaining/time_total
    failed_mvalue = failed_bid - cost_expected
    mvalue = bid - cost_expected
    chance_index = (max(0, (failed_mvalue-mvalue))/participants)*(1-risk_assessment)*(1-time_ratio)
    f_index = (max(0, mvalue)/cost_expected)*risk_assessment
    return chance_index*f_index


#import ols
#data = dbUtils.makeQueryList("SELECT ((winning_bid > 0)*(((cost_true - winning_bid))/cost_true)) AS margin, requirements, date_opened FROM Procurements WHERE state='closed' ORDER BY date_opened DESC LIMIT 10")
#data = np.array(data)
##data = randn(100,5)
#print(data[:, 1:])
#y = data[:,0]
#x = data[:,1:]
#mymodel = ols.ols(y,x,'y',['x1','x2'])
##mymodel.p               # return coefficient p-values
#print(mymodel.get_dict())


from calc import *
def learn():
    table = "bidder10_x220_chakra_pc_5188Procurements"
    wonList = dbUtils.makeQueryList("SELECT (B.won * abs((B.bid)/(B.cost_expected)) ) AS y, ((B.bid - B.cost_expected + B.private_value)/(B.cost_expected - B.private_value)) AS x1, P.requirements AS x2 FROM Procurements AS P LEFT JOIN "+table+" AS B ON B.Id=P.Id WHERE B.participating=1  AND P.state='closed' AND won=1 ORDER BY P.date_opened DESC LIMIT 10")
    lostList = dbUtils.makeQueryList("SELECT (B.won * abs((B.bid)/(B.cost_expected)) ) AS y, ((B.bid - B.cost_expected + B.private_value)/(B.cost_expected - B.private_value)) AS x1, P.requirements AS x2 FROM Procurements AS P LEFT JOIN "+table+" AS B ON B.Id=P.Id WHERE B.participating=1  AND P.state='closed' AND won=0 ORDER BY P.date_opened DESC LIMIT 10")
    pastList = wonList+lostList
    print("List: "+str(pastList))
    if (len(wonList) > 0 and len(lostList) > 0):
        popt = calc.learn_coef(pastList)
        print("popt: "+str(popt))
        print(calc.optimize_bid(popt, 0.5))
learn()

