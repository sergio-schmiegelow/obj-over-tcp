import logging
import obj_over_tcp as oot
import time

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')

myCnx = oot.objOverTcp('client', '127.0.0.1', 10000)
while True:
    event = myCnx.poll()
    if event is not None:
        print(f'client event = {event}')
        if event.eventType == oot.eventTypes.CONNECTED:
            myCnx.send('message')
    time.sleep(0.1)
''''''    
myDict = {'a':1, 'b':2}
myCnx.send(myDict)
obj = myCnx.receive(1)
logging.debug(obj)
''''''
