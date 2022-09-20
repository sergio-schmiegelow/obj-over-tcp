import asyncio
from csv import reader
import logging
import pickle
import select
import socket
from enum import Enum, unique
from types import SimpleNamespace
import sys


SELECT_TIME = 0.1
BUFFER_SIZE = 2048
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

@unique
class eventTypes(Enum):
    ERROR           =  1
    CONNECTED       =  2
    DISCONNECTED    =  4
    DATA_RECEIVED   =  8
    OBJECT_RECEIVED = 16
    DATA_SENT       = 32
    MORE_TO_DO      = 64

DEFAULT_EVENTS = sum([event.value for event in list(eventTypes)])
#-------------------------------------------------------------------------
def encode(obj):
    objBytes = pickle.dumps(obj)
    objSize = len(objBytes)
    sizeBytes = bytes(f'{objSize:8X}', 'utf8')
    return sizeBytes + objBytes
#-------------------------------------------------------------------------
class streamDecoder:
    def __init__(self):
        self.objSize = None
        self.objBuffer = b''
        self.objsList = []
    #-------------------------------------------------------------------------
    def insertBytes(self, data):
        self.objBuffer += data
        while len(self.objBuffer) > 0:
            if self.objSize is None:
                if len(self.objBuffer) >= 8:
                    sizeBytes = self.objBuffer[:8]
                    self.objBuffer = self.objBuffer[8:]
                    self.objSize = int(sizeBytes, base = 16)
                else:
                    break
            if self.objSize is not None:
                if len(self.objBuffer) >= self.objSize:
                    objBytes = self.objBuffer[:self.objSize]
                    self.objBuffer = self.objBuffer[self.objSize:]
                    obj = pickle.loads(objBytes)
                    logging.debug(f'object with {sys.getsizeof(obj)} bytes was received')
                    self.objsList.append(obj)
                    self.objSize = None
                else:
                    break
    #-------------------------------------------------------------------------
    def thereIsObject(self):
        return len(self.objsList) > 0
    #-------------------------------------------------------------------------
    def getObject(self):
        if len(self.objsList) > 0:
            return self.objsList.pop(0)
        else:
            return None
#-------------------------------------------------------------------------
class simpleTcp:
    #---------------------------------------------------------------------
    def __init__(self, side, address, port):
        if side not in ['server', 'client']:
            raise ValueError("The side attribute must be 'server' or 'client'")
        if type(address) is not str:
            raise TypeError('The address attribute must be str')
        if type(port) is not int:
            raise TypeError('The port attribute must be int')
        if not 0 < port < 65535:
            raise ValueError('The port attribute must be a int between 0 and 65535')
        self.side        = side
        self.address     = address
        self.port        = port
        self.connections = {}
        self.pendingEvents = []
        if self.side == 'server':
            try:
                self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.listener.bind((self.address, self.port))
                self.listener.setblocking(0)
                self.listener.listen()
            except Exception as e:
                self.pendingEvents.append(SimpleNamespace(eventType  = eventTypes.ERROR,
                                                          ootObj     = self,
                                                          data       = None,
                                                          connection = None,
                                                          errorMsg   = e))
    #---------------------------------------------------------------------
    def getConnectionFromSocket(self, sock):
        return [c for c in self.connections.keys() if c[0] == sock][0]
    #---------------------------------------------------------------------
    def poll(self):
        logging.debug(f'{self.side} simpleTcp.pool()')
        moreToDo = False
        if len(self.pendingEvents) > 0:
            return self.pendingEvents.pop(0)
        if self.side == 'server':
            logging.debug(f'{self.side}Checking for incomming connections')
            try:
                connection =  self.listener.accept()
            except:
                pass
            else:
                self.connections[connection] = {'txBuffer':b''}
                logging.debug(f'{self.side}New connection')
                self.pendingEvents.append(SimpleNamespace(eventType  = eventTypes.CONNECTED,
                                          data       = None,
                                          connection = connection,
                                          errorMsg   = None))
        else: #client
            if len(self.connections) == 0:
                logging.debug(f'{self.side} Trying to connect')
                try:
                    self.clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.clientSock.connect((self.address, self.port))
                except:
                    logging.debug(f'{self.side} Fail to connect')
                else:
                    logging.debug(f'{self.side} Connected')
                    connection = (self.clientSock, self.address)
                    self.connections[connection] = {'txBuffer':b''}
                    self.pendingEvents.append(SimpleNamespace(eventType  = eventTypes.CONNECTED,
                                              data       = None,
                                              connection = connection,
                                              errorMsg   = None))
        conectionsToRemove = []  
        readables = [c[0] for c in self.connections.keys()]
        writables = readables
        errorables = readables
        readables, writables, errorables = select.select(readables, writables, errorables, 0)
        logging.debug('Checking for incomming data')
        for sock in readables:
            logging.debug(f'{self.side} Receiving data from socket {sock}')
            incommingData = sock.recv(BUFFER_SIZE)
            if len(incommingData) > 0:
                moreToDo = True
                logging.debug(f'({self.side}) {len(incommingData)} bytes received')
                self.pendingEvents.append(SimpleNamespace(eventType  = eventTypes.DATA_RECEIVED,
                                                      data       = incommingData,
                                                      connection = self.getConnectionFromSocket(sock),
                                                      errorMsg   = None))
            else:
                logging.debug(f'{self.side} Disconnected')
                conectionsToRemove.append(self.getConnectionFromSocket(sock))
                self.pendingEvents.append(SimpleNamespace(eventType  = eventTypes.DISCONNECTED,
                                                      data       = None,
                                                      connection = self.getConnectionFromSocket(sock),
                                                      errorMsg   = None))
        logging.debug(f'{self.side} Checking for output data')
        for sock in writables:
            connection = self.getConnectionFromSocket(sock)
            txBuffer = self.connections[connection]['txBuffer']
            if len(txBuffer) > 0:
                logging.debug(f'{self.side} There is {len(txBuffer)} bytes to send on sock {sock}')
                bytesSent = sock.send(txBuffer, socket.MSG_DONTWAIT)
                logging.debug(f'{self.side} {len(txBuffer)} bytes were sent')
                txBuffer = txBuffer[bytesSent:]
                self.connections[connection]['txBuffer'] = txBuffer
                if len(txBuffer) > 0:
                    moreToDo = True
                else:
                    self.pendingEvents.append(SimpleNamespace(eventType  = eventTypes.DATA_SENT,
                                                              data     = None,
                                                              connection = connection,
                                                              errorMsg   = None)) 
        logging.debug(f'{self.side} Checking for errors')            
        for sock in errorables:
            logging.debug(f'{self.side} There is exception on socket {sock}')
            connection = self.getConnectionFromSocket(sock)
            self.pendingEvents.append(SimpleNamespace(eventType  = eventTypes.ERROR,
                                                      data       = None,
                                                      connection = connection,
                                                      errorMsg   = 'The socket was returned on the select.select exceptional list'))
            self.pendingEvents.append(SimpleNamespace(eventType  = eventTypes.DISCONNECTED,
                                                      data       = None,
                                                      connection = connection,
                                                      errorMsg   = None))
        for connection in conectionsToRemove:
            del self.connections[connection]
        if len(self.pendingEvents) > 0:
            return self.pendingEvents.pop(0)
        else:
            if moreToDo:
                return SimpleNamespace(eventType  = eventTypes.MORE_TO_DO,
                                       data       = None,
                                       connection = None,
                                       errorMsg   = None)
            return None
    #---------------------------------------------------------------------
    def isConnected(self):
        return len(self.connections) > 0
    #---------------------------------------------------------------------
    def getConnections(self):
        return self.connections.keys()
    #---------------------------------------------------------------------
    def close(self, connection = None):
        if connection is None:
            self.__del__()
        else:
            conn, address = connection
            conn.close()
            del self.connections[connection]
    #---------------------------------------------------------------------
    def __del__(self):
        if 'side' in self.__dict__.keys():
            if self.side == 'server':
                self.listener.close()
        if 'connections' in self.__dict__.keys():
            for connection in self.connections.keys():
                conn, address = connection
                conn.close()
        self.connections = {}    
    #---------------------------------------------------------------------
    def send(self, data, connection = None):
        if len(self.connections) == 0:
            logging.error('Not connected')
            return
        if connection is None:
            if self.side == 'server':
                logging.error('On server side, must specify a connection')
                return
            if self.side == 'client':
                connection = list(self.connections.keys())[0]
        self.connections[connection]['txBuffer'] += data
        logging.debug(f'{self.side}, {len(data)} bytes appended to txBuffer')
   
#-------------------------------------------------------------------------
class objOverTcp(simpleTcp):
    def __init__(self, side, address, port):
        super().__init__(side, address, port)
        self.decoder    = streamDecoder()
        self.eventsList = []
    #---------------------------------------------------------------------
    def poll(self):
        if len(self.eventsList) > 0:
            return(self.eventsList.pop(0))
        pollAgain = True #to consume all pending data
        while pollAgain: 
            event = super().poll()
            pollAgain = False
            if event is None:
                return None
            if event.eventType == eventTypes.DATA_RECEIVED:
                pollAgain = True
                self.decoder.insertBytes(event.data)
                while self.decoder.thereIsObject():
                    self.eventsList.append(SimpleNamespace(eventType  = eventTypes.OBJECT_RECEIVED,
                                                           object     = self.decoder.getObject(),
                                                           connection = event.connection,
                                                           errorMsg   = None))
            else:
                event.object = None
                self.eventsList.append(event)
        if len(self.eventsList) > 0:
            return(self.eventsList.pop(0))
        return None
    #---------------------------------------------------------------------
    def send(self, obj, connection = None):
        super().send(encode(obj), connection)
#-------------------------------------------------------------------------
class asyncSimpleTcp:
    #---------------------------------------------------------------------
    def __init__(self, side, address, port, callback, callbackEvents = DEFAULT_EVENTS, userData = None):
        if side not in ['server', 'client']:
            raise ValueError("The side attribute must be 'server' or 'client'")
        if type(address) is not str:
            raise TypeError('The address attribute must be str')
        if type(port) is not int:
            raise TypeError('The port attribute must be int')
        if not 0 < port < 65535:
            raise ValueError('The port attribute must be a int between 0 and 65535')
        if not callable(callback):
            raise TypeError('The callback attribute must callable')
 
        self.side           = side
        self.address        = address
        self.port           = port
        self.callback       = callback
        self.callbackEvents = callbackEvents
        self.userData       = userData
        self.connections    = []
        self.running        = True
        if self.side == 'server':
            self.serverTask  = asyncio.create_task(self.serverCoroutine())
        else: #client
            self.clientTask  = asyncio.create_task(self.clientCoroutine())
    #---------------------------------------------------------------------
    async def clientConnectedCallback(self, reader, writer):
        connection = (reader, writer)
        self.connections.append(connection)
        self.receiverTask  = asyncio.create_task(self.receiverCoroutine(connection))
        await self.callback(SimpleNamespace(eventType  = eventTypes.CONNECTED,
                                            astObj     = self,
                                            data       = None,
                                            userData   = self.userData,
                                            connection = connection,
                                            errorMsg   = None))
    #---------------------------------------------------------------------
    def isConnected(self):
        return len(self.connections) > 0
    #---------------------------------------------------------------------
    async def receiverCoroutine(self, connection):
        reader, writer = connection
        while True:
            if self.isConnected():
                try:
                    data = await reader.read(BUFFER_SIZE)
                except:
                    data = b''
                if len(data) == 0:
                    logging.debug('Disconnected')
                    self.connections.remove(connection)
                    if self.side == 'client' and len(self.connections) == 0:
                        self.running = False
                    await self.callback(SimpleNamespace(eventType  = eventTypes.DISCONNECTED,
                                                        astObj     = self,
                                                        data       = None,
                                                        userData   = self.userData,
                                                        connection = connection,
                                                        errorMsg   = None))
                    break
                await self.callback(SimpleNamespace(eventType  = eventTypes.DATA_RECEIVED,
                                                    astObj     = self,
                                                    data       = data,
                                                    userData   = self.userData,
                                                    connection = connection,
                                                    errorMsg   = None)) 
    #---------------------------------------------------------------------
    def getConnections(self):
        return self.connections
    #---------------------------------------------------------------------
    def isRunning(self):
        return self.running
    #---------------------------------------------------------------------
    async def serverCoroutine(self):
        try:
            self.server = await asyncio.start_server(self.clientConnectedCallback, self.address, self.port)
        except Exception as e:
            self.server = None
            self.running = False
            await self.callback(SimpleNamespace(eventType = eventTypes.ERROR,
                                                astObj     = self,
                                                data       = None,
                                                userData   = self.userData,
                                                connection = None,
                                                errorMsg   = e)) 
            return
           
        addrs = ', '.join(str(sock.getsockname()) for sock in self.server.sockets)
        logging.info(f'Serving on {addrs}')
    #---------------------------------------------------------------------
    async def clientCoroutine(self):
        try:
            connection = await asyncio.open_connection(self.address, self.port)
        except Exception as e:
            self.running = False
            await self.callback(SimpleNamespace(eventType  = eventTypes.ERROR,
                                                astObj     = self,
                                                object     = None,
                                                userData   = self.userData,
                                                connection = None,
                                                errorMsg   = e)) 
            return
        self.connections.append(connection)
        logging.debug("Client connected")
        self.receiverTask  = asyncio.create_task(self.receiverCoroutine(connection))
        await self.callback(SimpleNamespace(eventType  = eventTypes.CONNECTED,
                                            astObj     = self,
                                            object     = None,
                                            userData   = self.userData,
                                            connection = connection,
                                            errorMsg   = None)) 
        await self.receiverTask 
    #---------------------------------------------------------------------
    async def close(self, connection = None):
        if connection is None:
            for conn in self.connections:
                reader, writer = conn
                writer.close()
                await writer.wait_closed()
            if self.side == 'server':
                if self.server is not None:
                    self.server.close()
                    await self.server.wait_closed()
        else:
            reader, writer = connection
            writer.close()
            await writer.wait_closed()
        self.running = False
    #---------------------------------------------------------------------
    async def sendCoro(self, data, connection):
        reader, writer = connection
        writer.write(data)
        await writer.drain()
        await self.callback(SimpleNamespace(eventType  = eventTypes.DATA_SENT,
                                            astObj     = self,
                                            object     = None,
                                            userData   = self.userData,
                                            connection = connection,
                                            errorMsg   = None)) 
    #---------------------------------------------------------------------
    async def send(self, data, connection = None, blocking = False):
        if connection is None:
            if len(self.connections) == 0:
                logging.warning('Not connected')
                return
            else:
                innerConnection = self.connections[0]
        else:
            innerConnection = connection
        if blocking:
            reader, writer = connection
            writer.write(data)
            await writer.drain()
        else:
            asyncio.create_task(self.sendCoro(data, innerConnection))
#-------------------------------------------------------------------------
class asyncObjOverTcp(asyncSimpleTcp):
    #---------------------------------------------------------------------
    def __init__(self, side, address, port, userCallback, callbackEvents = DEFAULT_EVENTS, userData = None):
        super().__init__(side, address, port, self.innerCallback, callbackEvents, userData)
        self.userCallback = userCallback
        self.decoder      = streamDecoder()
    #---------------------------------------------------------------------
    async def innerCallback(self, event):
        event.ootObj = self
        if event.eventType == eventTypes.DATA_RECEIVED:
            self.decoder.insertBytes(event.data)
            while self.decoder.thereIsObject():
                event.object = self.decoder.getObject()
                event.eventType = eventTypes.OBJECT_RECEIVED
                await self.userCallback(event)
        else:
            event.object = None
            await self.userCallback(event)
    #---------------------------------------------------------------------
    async def send(self, obj, connection = None):
        await super().send(encode(obj), connection)