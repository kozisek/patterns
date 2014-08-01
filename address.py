import os
import socket
from tools import *
from random import randint
import re

class Addr(object):
    def __init__(self):
        super(Addr, self).__init__()
        if (Identifier.process_identifier == 0):
            Identifier.process_identifier = randint(1,9999)
        if hasattr(self, "name") and self.name:
            self.address = re.sub('[^0-9a-zA-Z]+', '_', self.name + "_" + socket.gethostname() + "_" + str(Identifier.process_identifier))
        else:
            pass

    def get_address(self):
        return self.address