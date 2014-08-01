#! /usr/bin/env python3
import simpy
from datetime import date, timedelta

class Scheduler():
    """
    Simulates the time flow.
    """
    env = simpy.Environment(0)
    def one(env, name, timeout):
        yield env.timeout(timeout)
        #env.process(one(env, 'only two', 11-tick))
        #time.sleep(10)
        #env.process(one(env, 'only one', 2))
        print(name, env.now,)
    #def __init__(self, start=date(2013, 1, 1)): #constructor
        #self.env = simpy.Environment(0)