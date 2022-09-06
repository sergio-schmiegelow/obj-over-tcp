import logging
import obj_over_tcp as oot
import time

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')

myServer = oot.objOverTcp('server', '0.0.0.0', 10000)

while True:
    event = myServer.poll()
    if event is not None:
        print(f'server event = {event}')
        if event.eventType == oot.eventTypes.OBJECT_RECEIVED:
            myServer.send(event.object, event.connection)
    time.sleep(0.1)
