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

from random import *
import sys
#from time import sleep
from address import Addr
from scheduler import Scheduler
from constants import Constants
#from rules import Legal, Config
#from register import Register
from database import *
import simpy
from tools import *
import time

env = simpy.Environment(0)

class Entities():
    """
    Makes possible to write values to the model.
    """
    def __init__(self, name=None, ): #generate all
        self.bidders = {}
        self.authorities = {}
        self.procurements = {}

entities = Entities()


class Bidder(Addr):
    """
    This class represents a company that participates 
    in procurement auctions.
    Notes: In order to do second level research, one must
    do in first level research. There is one database (list)
    for known procurements (procurements that have been
    through first level research) and another one for
    examined procurements (second level research). One can
    participate in an auction only for procurements that
    have been examined.
    """
    def __init__(self, name=None, ): #constructor
        self.name = name
        super(Bidder, self).__init__()
        self._inbussiness = True # if the company is still in bussiness
        self.address = self.get_address()
        #self._credit = 100 # credit score
        self._note = ""
        self._last_auctions = []
        #_market_knowledge: knowledge of the market, between 0 (no knowledge) and 1 
        self._market_knowledge = 0.99 # (perfect knowledge)
        self._market_individuality = 0.001
        self.size = random()*2
        # risk_assessment: how the company behaves in auctions
        # - risky behavior 1, safe behavior 0
        self.risk_assessment = 1 # how the company is willing to risk ( <1 risk averse, >1 risk seeking)
        #self.specialization = random() # how the company is specialized
        self.target_budget = register.avg_budget*self.size
        self.budget = self.target_budget
        dbUtils.query("CREATE TABLE IF NOT EXISTS "+self.address+"Procurements(Id TEXT PRIMARY KEY, cost_expected REAL, private_value REAL, price_added_expected REAL, passed BOOLEAN, participating BOOLEAN, won BOOLEAN DEFAULT 0, bid REAL DEFAULT 0 );")
        env.process(self.learning())
        env.process(self.weekly_check())
        self.popt = None

    def weekly_check(self):
        while True:
            yield env.timeout(round(abs(normalvariate(Config.weekly_check_days, Config.weekly_check_days/2))))
            if (env.now > Legal.min_submission_days_over):
                self.budget += -self.budget/11
                #self.budget += -register.average_amount_per_week*Constants.procurement_market_fraction
            if (Config.variable_risk_assessment):
                self.risk_assessment = self.budget/self.target_budget
            if not (0.1 < self.risk_assessment < 2):
                """
                Reducing/expanding company size.
                """
                self.target_budget = self.budget
            self.new_auction()
    
    def bankrupt(self):
        try:
            del(entities.bidders[self.address])
        except KeyError:
            self.budget = self.target_budget
    def alive(self):
        return True
    
    def learning(self):
        env.timeout(Config.bidder_learning_period)
        while True:
            yield env.timeout(Config.bidder_learning_period)
            self.learn()
    
    def learn(self):
        """
        Analyze previous auctions in which they participated and adjust the behavior accordingly. Uses curve fit to approximate function of success in auctions.
        """
        if ((self.budget < 0) and Config.variable_risk_assessment):
            print("BANKRUPT")
            self.bankrupt()
        wonList = dbUtils.makeQueryList("SELECT (B.won * (B.bid/(P.cost_true - B.private_value)-1) ) AS y, (B.bid/(P.cost_true - B.private_value)-1) AS x1, P.requirements AS x2 FROM "+Identifier.procurements+" AS P LEFT JOIN "+self.address+"Procurements AS B ON B.Id=P.Id WHERE B.participating=1  AND P.state!='open' AND B.won=1 AND (B.bid > cost_expected) ORDER BY P.date_opened DESC LIMIT "+str(Config.company_max_learning_data))
        lostList = dbUtils.makeQueryList("SELECT (B.won * (B.bid/(P.cost_true - B.private_value)-1) ) AS y, (B.bid/(P.cost_true - B.private_value)-1) AS x1, P.requirements AS x2 FROM "+Identifier.procurements+" AS P LEFT JOIN "+self.address+"Procurements AS B ON B.Id=P.Id WHERE B.participating=1  AND P.state!='open' AND B.won=0 AND (B.bid > cost_expected) ORDER BY P.date_opened DESC LIMIT "+str(Config.company_max_learning_data))
        pastList = wonList+lostList
        if ((len(pastList) > Constants.company_learning_coefficients) and (len(wonList) >= Config.company_min_learning_data and len(lostList) >= Config.company_min_learning_data)):
            #print("experienced")
            try:
                self.popt = calc.learn_coef(pastList)
            except:
                print("learning error")
        else:
            #print("not enough experience:"+str(len(wonList))+", "+str(len(lostList)))
            pass
    
    def won_auction(self, info_dict, t=0):
        """
        Receives notification that an auction has been won and acts accordingly.
        """
        dbUtils.query("UPDATE "+self.address+"Procurements SET won=1 WHERE Id='"+info_dict['Id']+"'")
        private_info = dbUtils.makeQuery("SELECT private_value FROM "+self.address+"Procurements WHERE Id='"+info_dict['Id']+"'")[0]
        self.budget += (info_dict['bid'] - info_dict['cost_true'] + private_info['private_value'])
                
    def new_auction(self, procurement={}, market_margin=Config.market_margin):
        """
        Applies for new procurement auction.
        """
        #info = self.procurement_research(procurement['ID'])
        specialization = uniform(0,1)
        cost_expected_sql = ['NORMAL_DIST(P.cost_true, (P.cost_true*(1-'+str(self._market_knowledge)+')))', 'P.auth_cost_expected'][Legal.expected_cost_public]
        selectquery = """
        SELECT P.Id AS Id, """+cost_expected_sql+""" AS cost_expected, NORMAL_DIST(0, (P.cost_true*"""+str(self._market_individuality)+""")) AS private_value,  random()%(10-5)+5 AS price_added_expected, (CASE WHEN """+str(specialization)+""" > P.requirements THEN 1 ELSE 0 END) AS passed, 0, 0, 0  FROM """+Identifier.procurements+""" AS P
            WHERE P.Id NOT IN
        (
            SELECT  Id
            FROM """+str(self.address)+"""Procurements AS B
        )
        """
        sql="""
        INSERT INTO """+str(self.address)+"""Procurements
        """+selectquery
        dbUtils.query(sql)
        sql = """
        SELECT B.cost_expected AS cost_expected, B.private_value AS private_value, P.requirements AS requirements, P.Id AS Id, MAXIMIZE(B.cost_expected, """+str(market_margin)+""", B.private_value, P.requirements, P.z_index, """+str(self.risk_assessment)+""") AS expected_value, (1 + ABS(NORMAL_DIST("""+str(market_margin)+"""+(B.private_value/B.cost_expected), ("""+str(market_margin/10)+""")))) AS test, P.cost_true AS cost_true FROM """+Identifier.procurements+""" AS P
            LEFT JOIN """+self.address+"""Procurements AS B
                ON P.Id = B.Id
        WHERE NOT B.participating AND state='open' AND passed=1
        ORDER BY (expected_value/(cost_expected-private_value)) LIMIT 1
        """
        result = dbUtils.makeQuery(sql)
        if result:
            if (self.popt == None) :
                #bid = abs(normalvariate(market_margin, market_margin*(0.01)))
                bid = calc.random_bid(result[0]['cost_expected'], result[0]['private_value'])
                self.auction_bid(result[0]['Id'], bid, result[0]['cost_true'], result[0]['private_value'])
            else:
                margin = calc.optimize_bid(self.popt, result[0]['requirements'], self.risk_assessment)
                self.auction_bid(result[0]['Id'], (result[0]['cost_expected']-result[0]['private_value'])*(1+margin), result[0]['cost_true'], result[0]['private_value'])
                
    
    def auction_bid(self, auction_id, bid, check_cost, private_value, t=0):
        """
        Makes the necessary steps after the decision to
        participate in an auction has been made.
        """
        entities.procurements[auction_id].bid(self.address, bid, check_cost, private_value)
        dbUtils.query("UPDATE "+self.address+"Procurements SET bid="+str(bid)+", participating=1 WHERE Id='"+auction_id+"'")

class Authority(Addr):
    """
    Motivation: the lowest price and the greatest goodwill.
    """
    def __init__(self, name=None, procurements_avg=Config.procurements_per_authority, years=Config.years, kind=None, trust=1, budget=Config.authority_budget, _market_knowledge=0.90):
        #constructor
        self.name = name
        super(Authority, self).__init__()
        self.kind = kind
        self.address = self.get_address()
        self._market_knowledge = _market_knowledge
        self.nuts = "01"
        self.budget = budget*Config.years # overall budget for the model, if constant
        self.trust = trust # Trustworthinness
        self.procurements_schedule(procurements_avg, years)
        self.procurement_count = 0
        self.goodwill = 0
        self.coefficients = {} # learning coefficients
        
        if (Legal.auth_learn_per_year > 0):
            env.process(self.learn()) # learning process

    def procurements_schedule(self, procurements_avg, years):
        """
        Schedules procurements for a given number of years.
        """
        for year in range(years):
            if Config.import_csv:
                """
                Import csv values.
                """
                self.budget = 0
                costs_final = sample(dbUtils.csvList, procurements_avg)
                for cost in costs_final:
                    self.budget += cost
            else:
                costs = sorted([randint(0, round(self.budget)) for p in range(0,procurements_avg)])
                costs_final = [costs[0]]
                for n,value in enumerate(costs):
                    if (n > 0):
                        costs_final.append(abs(costs[n]-costs[n-1]))
            dates=[randint((Constants.WORKDAYS*year),
                           (Constants.WORKDAYS*(year+1))) for p in range(0,procurements_avg)]
            for m,date in enumerate(dates):
                env.process(self.procurement_create(date, costs_final[m]))
            # YEAR REPORT
            env.process(self.year_report(year, Constants.WORKDAYS*(year+1)))
            # budget correction
            self.budget = auth_cost_expected = normalvariate(self.budget, (self.budget*(1-self._market_knowledge)))*(1+(randint(1, round(Config.market_margin*100))/100))
        #logging.debug(self.name+" scheduled "+str(years*procurements_avg)+" procurements in "+str(years)+" years.")
        return "Created "+str(years*procurements_avg)+" procurements in "+str(years)+" years."

    def procurement_create(self, t, cost_true=None, procurement_kind=None, auction_type="envelopes", market_margin=Config.market_margin):
        """
        Creates procurement on a given date. Procurement must have some properties:
        DATE - date of creation
        DUE DATE - date of decision
        AUTHORITY_TYPE
        PROCUREMENT_TYPE
        AUCTION_TYPE
        CRITERIA - just price, for now
        """
        yield env.timeout(t)
        if ((Legal.auth_learn_per_year > 0) and any(self.coefficients)):
            max_index = calc.max_from_list([self.coefficients['req1'], self.coefficients['req2'], self.coefficients['req3'], self.coefficients['req4']])
            tmplist = []
            for i in range(4):
                if (i == max_index):
                    tmplist.append(2)
                else:
                    tmplist.append(1)
            chosen_index = calc.weighted_choice(tmplist)
            req_range = [[0,0.25], [0.25, 0.5], [0.5, 0.75], [0.75, 1] ][chosen_index]
        else:
            req_range = [0,1]
        requirements = uniform(req_range[0], req_range[1])
        creation_date = t
        authority_kind = self.kind
        procurement_kind = procurement_kind
        auction_type = auction_type
        if not cost_true:
            cost_true = randint(10000,100000)
        price_added_expected = randint(1,round(Config.market_margin*100)) # percentage
        auth_cost_expected = normalvariate(cost_true, (cost_true*(1-self._market_knowledge)))*(1+(price_added_expected/100))
        price_expected = auth_cost_expected*(1+market_margin)
        if (price_expected > Legal.financial_limit):
            due_window = Legal.min_submission_days_over + abs(normalvariate(0, Legal.min_submission_days_over))  # how many days to apply
        else:
            due_window = Legal.min_submission_days_under + abs(normalvariate(0, Legal.min_submission_days_under))
        due_date = creation_date + due_window
        procurement = Procurement(name=self.name+"_procurement"+str(self.procurement_count),
                                  price_expected=price_expected,
                                  auth_cost_expected=auth_cost_expected,
                                  cost_true=cost_true,
                                  authority=self.address, auction_type=auction_type,
                                  nuts=self.nuts, state="open", date_opened=t,
                                  date_deadline=due_date, requirements=requirements)
        procurement_id = procurement.get_address()
        entities.procurements[procurement_id] = procurement
        self.procurement_count += 1
        info = procurement.get_info()

    def properties_random(self):
        """
        Randomly generates procurement's properties.
        """
        pass
    
    def properties_learned(self):
        """
        Generates procurement's properties with respect to past experiences.
        """
        pass
    
    def get_trust(self):
        return self.trust
    
    def learn(self):
        """
        Learn from previous auctions to find out which properties are best for the outcome.
        """
        while True:
            yield env.timeout(Constants.WORKDAYS/Legal.auth_learn_per_year)
            data = dbUtils.makeQueryList("SELECT ((winning_bid > 0)*(((cost_true - winning_bid))/auth_cost_expected)) AS margin, (requirements < 0.25) AS req1, (requirements >=0.25 AND requirements < 0.5 ) AS req2, (requirements >=0.5 AND requirements < 0.75 ) AS req3, (requirements >=0.75) AS req4, ((date_deadline - date_opened) - (CASE WHEN price_expected > "+str(Legal.financial_limit)+" THEN "+str(Legal.min_submission_days_over)+" ELSE "+str(Legal.min_submission_days_under)+" END)) AS due_window_added FROM "+Identifier.procurements+" WHERE state!='open' AND authority = '"+self.address+"' ORDER BY date_opened DESC LIMIT "+str(Legal.auth_max_learning_data))
            try:
                if (len(data) > Legal.auth_min_learning_data):
                    self.coefficients = calc.lm(data, ['req1', 'req2', 'req3', 'req4', 'due_window_added'])
            except:
                pass
            
    
    def year_report(self, year, t):
        yield env.timeout(t-1)
        result = dbUtils.makeQuery("SELECT * FROM "+Identifier.procurements+" WHERE authority='"+self.address+"' AND date_deadline > "+str(Constants.WORKDAYS*year)+" AND date_deadline <= "+str(Constants.WORKDAYS*(year+1)))
    
    def closed_auction(self, info_dict, market_margin=Config.market_margin):
        if (info_dict['state'] == 'auctioned'):
            self.budget += -info_dict['bid']
            self.goodwill += ((info_dict['cost_true']*(1+market_margin))-info_dict['bid'])+info_dict['cost_true']*market_margin
            #print(info_dict['bid']/(info_dict['cost_true_private']))
        else:
            self.procurement_create(1, info_dict['cost_true'])
            self.goodwill += -(info_dict['cost_true']*market_margin)

class Procurement(Addr):
    """
    Procurement. It is an entity that has a reference
    in the Register of Procurements. It can have
    multiple states and it can be also destroyed,
    but the information exists forever in the register.
    The Procurement entity has methods that handle
    communication with the register. For example,
    when the 'destroy' action is called, it first
    changed the state in the Register and then destroys
    itself.
    """
    def __init__(self, name=None, price_expected=None, auth_cost_expected=None,
                 cost_true=None, authority=None,
                 auction_type=None, procurement_kind=None,
                 nuts=None, state="open", date_opened=None, 
                 date_deadline=None, requirements=0, address=None): #constructor
        self.name = name
        #self.address = self.get_address()
        self.authority = authority
        self.date_opened = date_opened
        self.date_deadline = date_deadline
        self.date_window = date_deadline - date_opened
        self.auction_type = auction_type
        self.procurement_kind = procurement_kind
        self.nuts = nuts
        self.requirements = requirements
        self.state = 'open'
        self.price_expected = price_expected 
        self.auth_cost_expected = auth_cost_expected 
        self.cost_true = cost_true 
        self.bids = []
        super(Procurement, self).__init__()
        self.info_dict = { 'Id': self.get_address(),
                          'name': self.name,
                          'price_expected': self.price_expected,
                          'auth_cost_expected': self.auth_cost_expected,
                          'cost_true': self.cost_true, 'state': self.state,
                          'authority': self.authority, 'auction_type': self.auction_type,
                          'procurement_kind': self.procurement_kind,
                          'nuts': self.nuts,
                          'date_opened': self.date_opened,
                          'date_deadline': self.date_deadline,
                          'requirements': self.requirements, 
                          'authority_trust': entities.authorities[self.authority].get_trust() }
        self.address = self.info_dict['Id']
        register.new(self.info_dict)
        dbUtils.query("CREATE TABLE IF NOT EXISTS "+self.address+"Bids(Id INTEGER PRIMARY KEY, bidder TEXT, bid REAL, private_value REAL);") # Id is an address of the bidder
        env.process(self.evaluation(self.date_window))
    
    def __enter__(self):
        return self

    def bid(self, bidder_id, amount, check_cost, private_value):
        """
        Adds a bid.
        """
        self.cost_true = check_cost
        dbUtils.cursor.execute("INSERT OR REPLACE INTO "+self.address+"Bids VALUES(NULL, ?, ?, ?)", (bidder_id, amount, private_value))
        if (self.auction_type == "electronic"):
            self.lastBid = dbUtils.makeQuery("SELECT * FROM "+self.address+"Bids ORDER BY bid ASC LIMIT 1")[0]

    def evaluation(self, t):
        #if (self.auction_type == 'envelopes'):
        yield env.timeout(t)
        bids = dbUtils.makeQuery("SELECT * FROM "+self.address+"Bids ORDER BY bid ASC")
        register.close(self.address, self.info_dict, bids)
            
    
    def get_bids(self):
        return self.bids

    def get_info(self):
        return self.info_dict
    
    def __exit__(self, type, value, traceback):
        dbUtils.query("DROP TABLE "+self.address+"Bids")
        dbUtils.query("UPDATE "+Identifier.procurements+" SET state!='open' WHERE Id='"+self.address+"'")
    
class Register():
    """
    Register of public procurements.
    NUTS - the region code
    """
    def __init__(self): #constructor
        self.average_amount_per_week = ((((Config.authority_budget/(Config.years*Constants.WORKDAYS))*Config.weekly_check_days ) * Config.authorities )/Config.companies )
        self.initTime = time.time()
        if (Config.variable_market_margin or Config.variable_risk_assessment):
            """
            Check every year for current market margin and create new companies on the market to emulate Crowding in
            """
            env.process(self.year_check())
        if (Config.performance_logging_period > 0):
            env.process(self.logger())
        self.budget = 0
        self.avg_budget = 0
       
    def logger(self):
        while True:
            yield env.timeout(Config.performance_logging_period)
            self.average_amount_per_week = ((((self.avg_budget/(Constants.WORKDAYS))*Config.weekly_check_days ) * Config.authorities )/Config.companies )
            logging.debug(str(env.now)+", "+str(time.time()-self.initTime))
            print(env.now)

    def return_dict(self, cursor, row):
        """
        Helper to return dictionary.
        """
        dictionary = {}
        for i, column in enumerate(cursor.description):
            dictionary[column[0]] = row[i]
        return dictionary

    def new(self, data):
        """
        Inserts dictionary into the database.
        Also calculates the z_index as it is then available to all.
        """
        data['z_index'] = calc.z_index(data)
        query_str = "INSERT OR IGNORE INTO "+Identifier.procurements+"({}) VALUES({})"
        columns, values = zip(*data.items())
        query = query_str.format(",".join(columns),",".join("?"*len(values)))
        dbUtils.cursor.execute(query,values)
        dbUtils.connection.commit()
    
    def info(self, Id):
        """
        Returns detailed information about given procurement.
        """
        return dbUtils.makeQuery("SELECT ID as ID FROM "+Identifier.procurements+" WHERE Id='"+Id+"'")
    
    def close(self, procurement_id, info_dict, bids):
        """
        Closes given auction and notifies the authority of its result.
        """
        info_dict['bidders'] = len(bids)
        if (Legal.choose_random_offer and (len(bids) > 0)):
            try:
                bid_n = randrange(len(bids)-1)
            except:
                bid_n = 0
            info_dict['bidder'] = bids[bid_n]['bidder']
        else:
            bid_n = Legal.choose_n_th_offer
            if (len(bids) > 0):
                info_dict['bidder'] = bids[0]['bidder'] # the lowest bidding bidder is chosen
        while bid_n < info_dict['bidders']:
            """
            Made for the purpose of choosing the very next bid in case the first/second/... bidder has gone bankrupt in the meanwhile.
            """
            try:
                entities.bidders[bids[bid_n]['bidder']].alive()
                if not (bids[bid_n]['bid'] >= 0):
                    raise KeyError
                info_dict['bidder'] = bids[bid_n]['bidder']
                break
            except KeyError:
                bid_n += 1
        if info_dict['bidders'] > bid_n:
            info_dict['bid'] = bids[bid_n]['bid']
            info_dict['cost_true_private'] = info_dict['cost_true'] - bids[bid_n]['private_value']
            if ((info_dict['bidders'] > Legal.min_bidders) and (((info_dict['bid']/info_dict['auth_cost_expected'])-1) < Legal.max_margin )):
                info_dict['state'] = 'auctioned'
                entities.bidders[info_dict['bidder']].won_auction(info_dict)
            else:
                info_dict['state'] = 'failed'
        else:
            info_dict['bid'] = 0
            info_dict['cost_true_private'] = info_dict['cost_true']
            info_dict['state'] = 'no_bids'
        entities.authorities[info_dict['authority']].closed_auction(info_dict)
        dbUtils.query("UPDATE "+Identifier.procurements+" SET state='"+info_dict['state']+"', winning_bid='"+str(info_dict['bid'])+"', bidders='"+str(len(bids))+"', cost_true_private='"+str(info_dict['cost_true_private'])+"' WHERE Id='"+info_dict['Id']+"'")
        try:
            del(entities.procurements[info_dict['Id']])
        except:
            pass
        
    def year_check(self):
        while True:
            yield env.timeout(Constants.WORKDAYS)
            avg_margin = dbUtils.makeQuery("SELECT AVG((winning_bid/cost_true)-1) as avg_margin FROM "+str(Identifier.procurements)+" WHERE state!='open' AND date_deadline < "+str(env.now)+" AND date_deadline >= "+str(env.now-Constants.WORKDAYS))[0]['avg_margin']
            if ((avg_margin > 2*Config.market_margin) and Config.variable_risk_assessment):
                for i in range(0, round(10*(avg_margin - Config.market_margin))):
                    agent = Bidder("bidder" + str(len(entities.bidders)))
                    entities.bidders[agent.get_address()] = agent
            if ((avg_margin > 0) and Config.variable_market_margin):
                Config.market_margin = avg_margin

register = Register()
