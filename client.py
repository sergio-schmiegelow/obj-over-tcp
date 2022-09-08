import logging
import obj_over_tcp as oot
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

myObject = {'echo test object': 'message string'}

myCnx = oot.objOverTcp('client', '127.0.0.1', 10000)
while True:
    event = myCnx.poll()
    if event is not None:
        if event.eventType == oot.eventTypes.CONNECTED:
            logging.info('Connected')
            myCnx.send(myObject)
            logging.info(f'Object {myObject} was sent')
        if event.eventType == oot.eventTypes.OBJECT_RECEIVED:
            logging.info(f'Object received: {event.object}') 
            myCnx.close()
            break
    time.sleep(0.1)

