#! /usr/bin/env python3
"""
Copyright (c) 2014, Jakub Kozisek
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the <organization> nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""

from database import *
from rules import *
from scipy.optimize import *
from random import *
import numpy as np
import ols

class Calc():
    #def __init__(self, cost_expected=None, private_value=None, market_margin=None, z_index=None, restriction=None, risk_assessment=None):
        ##variables
        #self.cost_expected = cost_expected
        #self.private_value = private_value # substracts from the cost - therefore if <0 then has negative effect, if >0 positive
        #self.market_margin = market_margin # percentage
        #self.z_index = z_index
        #self.restriction = restriction # not used for now - in the future this is an index between 0 and 1 that specifies how much restriction is put in the procurement properties. This index is a probability that a given company will satisfy the rules. In here, it could act as a factor as well - either in z-index
        #self.cost_private = cost_expected-private_value
        #self.risk_assessment = risk_assessment # risky behavior? 1-complete risk, 0 complete risk aversion

    def z_index(self, values):
        """
        Emulates simple z_index. DB
        """
        auction_type = values["auction_type"]
        nonempty=0
        for value in values:
            if values[value]:
                nonempty = nonempty + 1
        info_index=nonempty/len(values)
        # Openness index - type of auction
        if (auction_type == "open"):
            openness_index=1
        elif (auction_type == "narrow"):
            openness_index = 0.5
        elif (auction_type == "dialog"):
            openness_index = 0.25
        else:
            openness_index = 0
        "Authority index"
        authority_index = values['authority_trust']
        return info_index*openness_index*authority_index
    
    
    def calculateBasic(self, bidder): # bidder is a class
        #self.userSettings = dbUtils.loadPrivateSettings(user)
        selectquery = """
        SELECT P.Id, NORMAL_DIST(P.cost_true, (P.cost_true*(1-"""+str(bidder._market_knowledge)+"""))) AS cost_expected, NORMAL_DIST(0, (P.cost_true*"""+str(bidder._market_individuality)+""")) AS value_private,  random()%(10-5)+5 AS price_added_expected, (CASE WHEN ((random()%(10-5)+5)/10) > P.restriction THEN 1 ELSE 0 END) AS passed  FROM Procurements AS P
            WHERE P.Id NOT IN
        (
            SELECT  Id
            FROM """+str(bidder.address)+"""Procurements AS B
        )
        """
        sql="""
        INSERT INTO """+str(bidder.address)+"""Procurements
        """+selectquery
        dbUtils.query(sql)
        return 0
    
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
    
    def maximize_bid(self, cost_expected=None, market_margin=None, private_value=None, restriction=None, z_index=0, risk_assessment=0.5):
        #res = minimize(v_index, x0, method='nelder-mead',options={'xtol': 1e-8, 'disp': True})
        #print("maximize"+str(res))
        ranges = [cost_expected, 2*cost_expected]
        res = optimize.brute(self.v_index, (ranges,), finish=None)
        return res
    
    def random_bid(self, cost_expected, private_value, market_margin=Config.market_margin):
        """
        Returns random bid based on private value and market margin.
        """
        standard = np.random.normal()/5
        bonus = private_value/cost_expected
        margin = (market_margin-bonus)*(standard+1)
        return cost_expected* (1 + margin)
    
    def func(self, x, a, b, c, d, e, f, g):
        return a * x[0] + b * x[0]**2 + c * x[0]**3 + d * x[0]**4 + e * x[1] + f * x[1]**2 + g

    def func1(self, x, a, b, c):
        return a * np.exp(-b * (x[0] + x[1])) + c

    def learn_coef(self, xy):
        #print(list(xy))
        xy = np.array(xy)
        y = xy[:,0]
        x = xy[:,1:]
        #print(y)
        #print(x)
        #print("not popped")
        popt, pcov = curve_fit(self.func, x.T, y, maxfev=100000)
        #print("popped")
        return popt
    
    def optimize_bid(self, popt, restriction, risk_assessment, market_margin=Config.market_margin):
        ranges = (0, Legal.max_margin, market_margin*0.0001)
        res = brute(lambda x: -self.func([x, restriction], *popt), (ranges,), finish=None)
        #def mybounds(**kwargs):
            #x = kwargs["x_new"]
            #tmax = bool(np.all(x <= market_margin*2))
            #tmin = bool(np.all(x >= 0.0))
            #return tmax and tmin
        #res = basinhopping(lambda x: self.func([x, restriction], *popt), 0.01, accept_test=mybounds, callback=None)['x'][0]
        #print(res['fun'])
        return res*risk_assessment
    
    def learn_coef_single(self, xy):
        xy = np.array(xy)
        y = xy[:,0]
        x = xy[:,2]
        z = np.polyfit(x, y, 3)
        return z
    
    def optimize_bid_single(self, popt, restriction, market_margin=Config.market_margin):
        #ranges = slice(0, 2 * market_margin * 1000000)
        ranges = (0, market_margin*2, market_margin*0.0001)
        f = np.poly1d(popt)
        res = brute(lambda x: -f(x), (ranges,), finish=None)
        return res
    
    def lm(self, data, keywords):
        data = np.array(data)
        y = data[:,0]
        x = data[:,1:]
        model = ols.ols(y,x,'y',keywords)
        return model.get_dict()
    
    def randint(self, min, max):
        return randint(min, max)
    
    def max_from_list(self, values):
        """
        Returns the index of the maximal value from the list.
        """
        return np.argmax(values)
    
    def weighted_choice(self, weights):
        """
        Custom weighted choice to allow analyzing OLS results.
        """
        totals = []
        running_total = 0
        
        for w in weights:
            running_total += w
            totals.append(running_total)

        rnd = random() * running_total
        for i, total in enumerate(totals):
            if rnd < total:
                return i

    
calc = Calc()