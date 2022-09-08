import obj_over_tcp as oot
import time
import logging
#-------------------------------------------------------------------------
def test_client_server():
    myServer = oot.objOverTcp('server', '0.0.0.0',   10000)
    myCnx    = oot.objOverTcp('client', '127.0.0.1', 10000)
    serverResponse = None
    
    while True:
        event = myServer.poll()
        if event is not None:
            if event.eventType == oot.eventTypes.CONNECTED:
                logging.info(f'(server) Client connected')
            if event.eventType == oot.eventTypes.OBJECT_RECEIVED:
                myServer.send('response', event.connection)
                logging.info(f'(server) Object {event.object} was received object response was echoed')
            if event.eventType == oot.eventTypes.DISCONNECTED:
                logging.info(f'(server) Client disconnected')
        event = myCnx.poll()
        if event is not None:
            if event.eventType == oot.eventTypes.CONNECTED:
                logging.info('(client) Connected')
                myCnx.send('request')
                logging.info(f'Object request was sent')
            if event.eventType == oot.eventTypes.OBJECT_RECEIVED:
                logging.info(f'Object received: {event.object}') 
                serverResponse = event.object
                myCnx.close()
                break        
        time.sleep(0.1)
    myServer.close()
    assert serverResponse == 'response'
#-------------------------------------------------------------------------    
if __name__ == '__main__':
    test_client_server()