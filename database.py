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

import sqlite3
from random import *
from calc import *
import locale
from tools import *
from random import randint
import csv
from rules import *
from constants import *
pythenv = 3

class DatabaseUtils():
    def __init__(self):
        self.openDatabase()
        self.csvList = []
        self.csvIn()

    def openDatabase(self):
        def dict_factory(cursor, row):
            d = {}
            for idx, col in enumerate(cursor.description):
                    d[col[0]] = row[idx]
            return d

        def list_factory(cursor, row):
            return list(row)
        
        def convert_timestamp(time):
            return time
        
        def re_fn(expr, item):
            reg = re.compile(expr, re.I)
            return reg.search(item) is not None
        
        def normal_dist(mean, standard_error):
            #_expected = random.normalvariate(cost_true, (cost_true*(1-self._market_knowledge)))
            #_private = random.normalvariate(0, (cost_true*self._market_individuality))
            result = normalvariate(mean, standard_error)
            return result
        
        def maximize(cost_expected, market_margin, private_value, restriction, z_index, risk_assessment):
            result = (private_value+(cost_expected*(market_margin*risk_assessment)))*(restriction/0.5)
            return result
        
        def maximize_brute(cost_expected, market_margin,private_value, restriction, popt, risk_assessment):
            margin = calc.optimize_bid(popt, requirements, risk_assessment)
            return (cost_expected-private_value)*(1+margin)
        
        sqlite3.register_converter("TIMESTAMP",convert_timestamp)
        self.connection = sqlite3.connect(Config.database_name, detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)
        self.connection.create_function("REGEXP", 2, re_fn)
        self.connection.create_function("NORMAL_DIST", 2, normal_dist)
        self.connection.create_function("MAXIMIZE", 6, maximize)
        self.cursor_list=self.connection.cursor()
        self.connection.row_factory = dict_factory
        if pythenv==2:
            self.connection.text_factory = lambda x: unicode(x, "utf-8", "ignore")
        else:
            self.connection.text_factory = lambda x: str(x, 'utf-8')
        self.connection.create_collation("LEXICAL", locale.strcoll)
        #global cursor
        self.cursor=self.connection.cursor()
        if (Identifier.process_identifier == 0):
            Identifier.process_identifier = randint(1,9999)
            print("Modelling ID: "+str(Identifier.process_identifier))
        Identifier.procurements = "Procurements"+str(Identifier.process_identifier)
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS """+Identifier.procurements+"""(
            Id TEXT PRIMARY KEY,
            name TEXT,
            price_expected REAL,
            auth_cost_expected REAL,
            cost_true REAL,
            cost_true_private REAL,
            state TEXT,
            authority TEXT,
            auction_type TEXT,
            procurement_kind TEXT,
            nuts TEXT,
            date_opened INTEGER,
            date_deadline INTEGER,
            requirements REAL,
            authority_trust REAL,
            z_index REAL,
            winning_bid REAL DEFAULT 0,
            bidders INTEGER DEFAULT 0);""")
        self.connection.commit()

    def closeDatabase(self):
        self.connection.close()
        
    def makeQueryList(self, query):
        self.cursor_list.execute(query)
        results = self.cursor_list.fetchall()
        self.closeDatabase()
        return results

    def makeQuery(self, query):
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        self.closeDatabase()
        return results
    
    def query(self, query):
        """Basic edit query"""
        self.cursor.execute(query)
        self.connection.commit() 
        return 1
    
    def closeDatabase(self):
        #print("not closing")
        pass
        
    def getAll(self, table):
        """
        Select all from a table.
        """
        return self.makeQuery('SELECT * FROM '+table)
    
    def csvIn(self):
        try:
            csvFile = csv.DictReader(open("input.csv", 'r'))
            Config.import_csv = True
            for row in csvFile:
                self.csvList.append((int(row['price_expected'])/(1+Config.market_margin)))
        except:
            pass

    def csvDump(self, table=Identifier.procurements):
        dump = self.makeQuery("SELECT *, "+str(Legal.min_submission_days_over)+" AS min_submission_days_over, "+str(Legal.min_submission_days_under)+" AS min_submission_days_under, "+str(Legal.min_bidders)+" AS min_bidders, "+str(Legal.max_margin)+" AS max_margin, "+str(Legal.choose_n_th_offer)+" AS choose_n_th_offer, "+str(Legal.choose_random_offer*1)+" AS choose_random_offer, "+str(Legal.expected_cost_public*1)+" AS expected_cost_public, "+str(Legal.financial_limit)+" AS financial_limit, "+str(Config.procurements_per_authority)+" AS procurements_per_authority, "+str(Identifier.process_identifier)+" AS process_identifier FROM "+str(Identifier.procurements)+" WHERE state!='open' AND date_opened >= "+str((Config.log_from_year-1)*Constants.WORKDAYS))
        keys = list(dump[0].keys())
        print(keys)
        file_out = open(Config.output_csv_name+str(Identifier.process_identifier)+'.csv', 'w', newline='')
        dump_writer = csv.DictWriter(file_out, keys)
        dump_writer.writeheader()
        dump_writer.writerows(dump)
        return dump
    
dbUtils = DatabaseUtils()
