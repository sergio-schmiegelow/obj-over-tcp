import logging
import obj_over_tcp as oot
import time

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')

myCnx = oot.objOverTcp('client', '127.0.0.1', 10000)
myDict = {'a':1, 'b':2}
myCnx.send(myDict)
obj = myCnx.receive(1)
logging.debug(obj)
