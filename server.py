import logging
import obj_over_tcp as oot
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

myServer = oot.objOverTcp('server', '0.0.0.0', 10000)

while True:
    event = myServer.poll()
    if event is not None:
        if event.eventType == oot.eventTypes.CONNECTED:
            logging.info(f'Client connected')
        if event.eventType == oot.eventTypes.OBJECT_RECEIVED:
            myServer.send(event.object, event.connection)
            logging.info(f'Object {event.object} was received and echoed')
        if event.eventType == oot.eventTypes.DISCONNECTED:
            logging.info(f'Client disconnected')
    time.sleep(0.1)
