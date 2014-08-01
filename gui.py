#! /usr/bin/env python3

from generate import *
import pyotherside
#from tools import *

class Gui():
    def notify(self):
        while True:
            yield env.timeout((Config.years*Constants.WORKDAYS)/100)
            pyotherside.send('time', ((env.now)/(Config.years*Constants.WORKDAYS)))
            pass
    
    def runModel(self):
        generator.setup()
        env.process(self.notify())
        pyotherside.send('id', Identifier.process_identifier)
        generator.run()
        
    def refresh(self):
        reload(generate)
gui = Gui()
#gui.runModel()