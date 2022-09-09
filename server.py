import obj_over_tcp as oot
import time

myServer = oot.objOverTcp('server', '0.0.0.0', 10000)

while True:
    event = myServer.poll()
    if event is not None:
        if event.eventType == oot.eventTypes.CONNECTED:
            print(f'Client connected')
        elif event.eventType == oot.eventTypes.OBJECT_RECEIVED:
            myServer.send(event.object, event.connection)
            print(f'Object {event.object} was received and echoed')
        elif event.eventType == oot.eventTypes.DISCONNECTED:
            print(f'Client disconnected')
    time.sleep(0.1)
