import obj_over_tcp as oot
import time

myObject = {'echo test object': 'message string'}

myCnx = oot.objOverTcp('client', '127.0.0.1', 10000)
while True:
    event = myCnx.poll()
    if event is not None:
        if event.eventType == oot.eventTypes.CONNECTED:
            print('Connected')
            myCnx.send(myObject)
            print(f'Object {myObject} was sent')
        elif event.eventType == oot.eventTypes.OBJECT_RECEIVED:
            print(f'Object received: {event.object}') 
            myCnx.close()
            break
    time.sleep(0.1)

