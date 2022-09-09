# obj-over-tcp
Library to transport Python Objects over a TCP/IP connection

There are two operation modes: Synchronous and asyncronous.

In synchronous mode a objOverTcp (client ou server) object must me created and its poll method must be called periodically. The return of pool is an event or None.
## Echo client example in synchronous mode
```python
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
```
## Echo server example in synchronous mode
```python
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
```
In asynchronous mode, a callback async funcion must be defined to receive the events. A asyncObjOverTcp (client ou server) object must me created and the asyncio event loop must be run.
## Echo client example in asynchronous mode
```python
import asyncio
import obj_over_tcp as oot

async def callback(event):
    if event.eventType == oot.eventTypes.CONNECTED:
        await event.ootObj.send('my message') #can be any Python object
    elif event.eventType == oot.eventTypes.OBJECT_RECEIVED:
        print(f'Echo received:{event.object}')
        await event.ootObj.close()

async def main():
    myOOT = oot.asyncObjOverTcp('client', '127.0.0.1', 10000, callback)
    while myOOT.isRunning():
        #Other loop code here
        await asyncio.sleep(0.1)

asyncio.run(main())
```
## Echo client example in asynchronous mode
```python
import asyncio
import obj_over_tcp as oot

async def callback(event):
    if event.eventType == oot.eventTypes.CONNECTED:
        await event.ootObj.send('my message') #can be any Python object
    elif event.eventType == oot.eventTypes.OBJECT_RECEIVED:
        print(f'Echo received:{event.object}')
        await event.ootObj.close()

async def main():
    myOOT = oot.asyncObjOverTcp('client', '127.0.0.1', 10000, callback)
    while myOOT.isRunning():
        #Other loop code here
        await asyncio.sleep(0.1)

asyncio.run(main())
```
