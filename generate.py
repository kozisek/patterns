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

from model import *
from tools import *
from database import *
from imp import reload


class Generator():
    def generate_agents(self, prefix, count, type):
        def factory():
            agents = {}
            for i in range(count):
                agent = type(prefix + str(i))
                agents[agent.get_address()] = agent
                if (prefix == "authority"):
                    register.budget +=agent.budget
            return agents
        return factory()

    def setup(self):
        entities.authorities = self.generate_agents("authority", Config.authorities, Authority)
        register.avg_budget = register.budget/(Config.years*Config.companies)
        entities.bidders = self.generate_agents("bidder", Config.companies, Bidder)

        return "Set up"

    def run(self):
        env.run(until=Constants.WORKDAYS*Config.years)
        return dbUtils.csvDump()
    
    def runModel(self):
        self.setup()
        self.run()
generator = Generator()

if __name__ == "__main__":
    generator.runModel()