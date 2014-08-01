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
import os
import configparser
config = configparser.ConfigParser()
config.read(os.path.dirname(os.path.abspath(__file__))+"/patterns.ini")


class Legal():
    """
    The law.
    """
    min_submission_days_over = config.getint("Legal", 'min_submission_days_over') # Minimal number of days for companies to submit their auction offers.
    min_submission_days_under = config.getint("Legal", 'min_submission_days_under') # Minimal number of days for companies to submit their auction offers.
    min_bidders = config.getint("Legal", 'min_bidders') # Minimal number of bidders participating in auction.
    max_margin = config.getint("Legal", 'max_margin') # Minimal number of days for companies to submit their auction offers.
    choose_n_th_offer = config.getint("Legal", 'choose_n_th_offer')-1 # which offer should be chosen in the auction (0 - first, 1 - second, etc.)
    choose_random_offer = config.getboolean("Legal", 'choose_random_offer') # choosing random offer in the auction, 0 - no, 1 - yes
    expected_cost_public = config.getint("Legal", 'expected_cost_public') # whether authorities should share expected prices (0 no, 1 yes)
    auth_learn_per_year = config.getfloat("Legal", 'auth_learn_per_year') # how many times a year to do a check
    auth_min_learning_data = config.getint("Legal", 'auth_min_learning_data') # maximal number of procurements (of each type) company can go through learning and adjust its behavior. Should be more than 7 - number of coefficients.
    auth_max_learning_data = config.getint("Legal", 'auth_max_learning_data') # maximal number of procurements (of each type) company can go through learning and adjust its behavior. Should be more than 7 - number of coefficients.
    financial_limit = config.getint("Legal", 'financial_limit') # financial limit for procurements

class Config():
    """
    Model configuration
    """
    years = config.getint("Config", 'years')
    procurements_per_authority = config.getint("Config", 'procurements_per_authority')
    authorities = config.getint("Config", 'authorities')
    companies = config.getint("Config", 'companies')
    weekly_check_days = config.getint("Config", "weekly_check_days") # how many days before another check
    performance_logging_period = config.getint("Config", 'performance_logging_period') # how many days between logging - disabled if equal to zero
    database_name = config["Config"]['database_name'] # use ':memory:' for temporary database, 'patterns.db' as an example for local file
    output_csv_name = config["Config"]['output_csv_name'] # name of the final output file
    log_from_year = config.getint("Config", 'log_from_year') # from which year to generate output
    iterations = config.getint("Config", 'iterations') # number of times the modelling is repeated
    market_margin = config.getfloat("Config", 'market_margin')
    variable_risk_assessment = config.getboolean("Config", 'variable_risk_assessment') # whether companies' risk assessment should vary based on their financial condition - includes the possibility to go bancrupt
    company_min_learning_data = config.getint("Config", 'company_min_learning_data') # minimal number of procurements (of each type) company must go through to be able to learn and adjust its behavior
    company_max_learning_data = config.getint("Config", 'company_max_learning_data') # maximal number of procurements (of each type) company can go through learning and adjust its behavior. Should be more than 7 - number of coefficients.
    variable_market_margin = config.getboolean("Config", 'variable_market_margin') # whether market margin should be yearly recalculated - therefore would depend solely on the public procurement market
    fixed_computation_id = config.getint("Config", 'fixed_computation_id') # if larger than zero, then fixes the computation id to allow prefilling the database with custom values.
    bidder_learning_period = config.getint("Config", 'bidder_learning_period') # how often should bidders analyze their behavior
    authority_budget = config.getint("Config", 'authority_budget') # default budget size for an authority
    import_csv = False # if the import file is not available, do not import it

class Helper():
    def getLegal(self):
        return {'min_submission_days_over': Legal.min_submission_days_over, 'min_submission_days_under': Legal.min_submission_days_under, 'min_bidders': Legal.min_bidders, 'max_margin': Legal.max_margin, 'choose_n_th_offer': Legal.choose_n_th_offer, 'expected_cost_public': Legal.expected_cost_public, 'auth_learn_per_year': Legal.auth_learn_per_year}
    
    def saveLegal(self, dictionary):
        for key in dictionary.keys():
            value = str(dictionary[key])
            config['Legal'][key] = value.rstrip('0').rstrip('.') if '.' in value else value
        return value
        #with open('patterns.ini', 'w') as configfile:
            #config.write(configfile)
    
    def getConfig(self):
        return {'years': Config.years, 'procurements_per_authority': Config.procurements_per_authority, 'authorities': Config.authorities, 'companies': Config.companies, 'weekly_check_days': Config.weekly_check_days, 'performance_logging_period': Config.performance_logging_period, 'database_name': Config.database_name, 'output_csv_name': Config.output_csv_name, 'log_from_year': Config.log_from_year, 'iterations': Config.iterations}
    
    def saveConfig(self, dictionary):
        for key in dictionary.keys():
            value = str(dictionary[key])
            config['Config'][key] = value.rstrip('0').rstrip('.') if '.' in value else value
        with open('patterns.ini', 'w') as configfile:
            config.write(configfile)
helper = Helper()
