import logging
import obj_over_tcp as oot
import time

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')

myCnx = oot.objOverTcp('server', '0.0.0.0', 10000)
obj = myCnx.receive(1)
logging.debug(obj)
myDict = {'aa':11, 'bb':22}
myCnx.send(myDict)
time.sleep(1)
