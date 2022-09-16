import obj_over_tcp as oot
import time
import logging
import sys
#-------------------------------------------------------------------------
def test_client_server():
    myServer = oot.objOverTcp('server', '0.0.0.0',   10000)
    myCnx    = oot.objOverTcp('client', '127.0.0.1', 10000)
    serverResponse = None
    
    while True:
        moreToDo = False
        event = myServer.poll()
        if event is not None:
            moreToDo = True
            if event.eventType == oot.eventTypes.CONNECTED:
                logging.info(f'(test_sync - server) Client connected')
            if event.eventType == oot.eventTypes.OBJECT_RECEIVED:
                myServer.send('response', event.connection)
                logging.info(f'(test_sync - server) Object {event.object} was received object response was echoed')
            if event.eventType == oot.eventTypes.DISCONNECTED:
                logging.info(f'(test_sync - server) Client disconnected')
        event = myCnx.poll()
        if event is not None:
            moreToDo = True
            if event.eventType == oot.eventTypes.CONNECTED:
                logging.info('(test_sync - client) Connected')
                myCnx.send('request')
                logging.info(f'(test_sync - client) Object request scheduled to send')
            if event.eventType == oot.eventTypes.OBJECT_RECEIVED:
                logging.info(f'(test_sync - client) Object received: {event.object}') 
                serverResponse = event.object
                myCnx.close()
                break     
        if not moreToDo:
            time.sleep(0.1)
    myServer.close()
    assert serverResponse == 'response'
#-------------------------------------------------------------------------    
def test_echo_big_transfer():
    myServer = oot.objOverTcp('server', '0.0.0.0',   10000)
    myCnx    = oot.objOverTcp('client', '127.0.0.1', 10000)
    serverResponse = None
    bigObject = list(range(1000000))
    while True:
        moreToDo = False
        event = myServer.poll()
        if event is not None:
            moreToDo = True
            if event.eventType == oot.eventTypes.CONNECTED:
                logging.info(f'(server) Client connected')
            if event.eventType == oot.eventTypes.OBJECT_RECEIVED:
                myServer.send(event.object, event.connection)
                logging.info(f'(server) Object with len = {sys.getsizeof(event.object)} was received and echoed back')
            if event.eventType == oot.eventTypes.DISCONNECTED:
                logging.info(f'(server) Client disconnected')
        event = myCnx.poll()
        if event is not None:
            moreToDo = True
            if event.eventType == oot.eventTypes.CONNECTED:
                logging.info('(client) Connected')
                myCnx.send(bigObject)
                logging.info(f'(client)Object was scheduled to send')
            if event.eventType == oot.eventTypes.OBJECT_RECEIVED:
                logging.info(f'(client)Object with len = {sys.getsizeof(event.object)} was received') 
                serverResponse = event.object
                myCnx.close()
                break
        if not moreToDo:            
            time.sleep(0.1)
    myServer.close()
    assert serverResponse == bigObject
#-------------------------------------------------------------------------
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
if __name__ == '__main__':
    test_client_server()
    test_echo_big_transfer()