# obj-over-tcp
Library to transport Python Objects over a TCP/IP connection

There are two operation modes: Synchronous and asyncronous

In synchronous mode a objOverTcp (client ou server) object must be created and its poll method must be called periodically. The return of pool is an event or None
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
In asynchronous mode, a callback async function must be defined to receive the events. A asyncObjOverTcp (client ou server) object must be created and the asyncio event loop must be run
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
## Echo server example in asynchronous mode
```python
import asyncio
import obj_over_tcp as oot

async def callback(event):
    if event.eventType == oot.eventTypes.OBJECT_RECEIVED:
        print(f'Object received:{event.object}')
        await event.ootObj.send(event.object)
    elif event.eventType == oot.eventTypes.ERROR:
        print(f'ERROR: {event.errorMsg}')
        
async def main():
    myOOT = oot.asyncObjOverTcp('server', '0.0.0.0', 10000, callback)
    while myOOT.isRunning():
        #Other loop code here
        await asyncio.sleep(0.1)

asyncio.run(main())
```
## The event object 
The event object is a namespace with the following fields:

* **eventType**:
  * **eventTypes.ERROR**: Means some error occurred. The error message is on the errorMsg field
  * **eventTypes.CONNECTED**:
    * In client mode, means the requested connection is connected
    * In server mode, means there is a new connection
  * **eventTypes.DISCONNECTED**:
    * In client mode, means the requested connection is disconnected
    * In server mode, means one of the connections is disconnected
  * **eventTypes.OBJECT_RECEIVED**: Means an object is received. The object is on the object field
  * **eventTypes.DATA_SENT**: Means the data on the send command is sent
* **ootObj**: (Only in asynchronous mode) The asyncObjOverTcp object associated to the event. Usefull when there is more than one client ou server using the same callback function
* **object**: (Only if eventType == eventTypes.OBJECT_RECEIVED) The received object
* **userData**: The contents of the userData parameter on the creation of the asyncObjOverTcp object;
* **connection**:
    * In client mode, requested connection
    * In server mode, one of the connections
* **errorMsg**: (Only if eventType == eventTypes.ERROR) The error message

## Classes

---

### **class objOverTcp(side, address, port)**
* **side**: 'client' or 'server'
* **address**:
  * In client mode: remote IP or host name
  * In server mode: address of the interface to listen for connnections (Use '0.0.0.0' for all interfaces)
* **port** TCP port to connect(client mode) or to listen for connections(server mode)
####  Methods
* **poll()**: Must be called periodically to:
  * Establish new connections (server mode)
  * Receive objects
  * **returns**: An event object
* **send(obj, connection = None)**: Send a Python object
  * **Obj**: object to send
  * **connection**: 
    * In client mode: Not used
    * In server mode: The connection to be used to send the object
* **close(connection = None)**: Close a connection
  * **connection**: 
    * In client mode: Not used
    * In server mode: The connection to close. If None, all connections and the server will be closed

---

### **class asyncObjOverTcp(side, address, port, callback, callbackEvents = DEFAULT_EVENTS, userData = None)**
* **side**: 'client' or 'server'
* **address**:
  * In client mode: remote IP or host name
  * In server mode: address of the interface to listen for connnections (Use '0.0.0.0' for all interfaces)
* **port** TCP port to connect(client mode) or to listen for connections(server mode)
* **(async)callback**: function on template *async def f(event)*. It is called on:
  * New connections
  * Disconnections
  * New object received
  * Data sent
  * Errors
* **callbackEvents** Event types to generate the callback function call. It is an "OR" combination of:
  * **eventTypes.ERROR**
  * **eventTypes.CONNECTED**
  * **eventTypes.DISCONNECTED**
  * **eventTypes.OBJECT_RECEIVED**
  * **eventTypes.DATA_SENT**
  * (the default is all of them)
* **userData**: A Python object to be returned on the event on the callback .Usefull when there is more than one asyncObjOverTcp pointing to the same callback function
####  Methods
* **(async)send(obj, connection = None, blocking = False)**: Send a Python object
  * **Obj**: object to send
  * **connection**: 
    * In client mode: Not used
    * In server mode: The connection to be used to send the object
  * **Blocking** if True, will wait the object to be sent. If false, will call the callback function when the object is sent
* **(async)close(connection = None)**: Close a connection
  * **connection**: 
    * In client mode: Not used
    * In server mode: The connection to close. If None, all connections and the server will be closed
* **isConnected(self)**
  * Returns True if there is at least one connected connection
* **getConnections()**
  * Return a list of all connected connections
* **isRunning()**
  * In client mode: Returns True if it is connected or trying to connect
  * In server mode: Returns True if the there is connected connectins or the server is listening for new connections
  
---

## Stream transport classes

---

### **class simpleTcp(side, address, port)**
### **class asyncSimpleTcp(side, address, port, callback, callbackEvents = DEFAULT_EVENTS, userData = None)**
* The **simpleTcp** and **asyncSimpleTcp** are similar respectively to  **objOverTcp** and **asyncObjOverTcp**. The differences are:
  * Stream based:
    * Send and receive bytes objects
    * The fragmentation of the sending may be different of the reception
  * Instead of **eventTypes.OBJECT_RECEIVED** the receiving event is **eventTypes.DATA_RECEIVED**
  * Instead fo **object** field, the data will come on the **data** field of the event object