import asyncio
from csv import reader
import logging
import pickle
import select
import socket
from enum import Enum, unique
from types import SimpleNamespace


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
                    logging.debug(f'object {obj} received')
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
        self.connections = []
        self.pendingEvent = None
        if self.side == 'server':
            try:
                self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.listener.bind((self.address, self.port))
                self.listener.setblocking(0)
                self.listener.listen()
            except Exception as e:
                self.pendingEvent = SimpleNamespace(eventType  = eventTypes.ERROR,
                                                    ootObj     = self,
                                                    data       = None,
                                                    connection = None,
                                                    errorMsg   = e)
    #---------------------------------------------------------------------
    def poll(self):
        if self.pendingEvent is not None:
            return self.pendingEvent
            self.pendingEvent = None
        if self.side == 'server':
            logging.debug('Checking for incomming connections')
            try:
                connection =  self.listener.accept()
            except:
                pass
            else:
                self.connections.append(connection)
                logging.debug('New connection')
                return SimpleNamespace(eventType  = eventTypes.CONNECTED,
                                       data       = None,
                                       connection = connection,
                                       errorMsg   = None)
        else: #client
            if len(self.connections) == 0:
                logging.debug('Trying to connect')
                try:
                    self.clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.clientSock.connect((self.address, self.port))
                except:
                    logging.debug('Fail to connect')
                else:
                    logging.debug('Connected')
                    connection = (self.clientSock, self.address)
                    self.connections.append(connection)
                    return SimpleNamespace(eventType  = eventTypes.CONNECTED,
                                           data       = None,
                                           connection = connection,
                                           errorMsg   = None)
        conectionsToRemove = []  
        eventToReturn = None         
        for connection in self.connections:
            conn, addr = connection
            logging.debug('Waiting incomming data')
            readable, writable, errorable = select.select([conn],[],[], 0)
            if conn in readable:
                data = conn.recv(BUFFER_SIZE)
                if len(data) > 0:
                    logging.debug(f'({self.side}) Data received:{data}')
                    return SimpleNamespace(eventType  = eventTypes.DATA_RECEIVED,
                                           data       = data,
                                           connection = connection,
                                           errorMsg   = None)
                else:
                    logging.debug(f'Disconnected')
                    conectionsToRemove.append(connection)
                    eventToReturn = SimpleNamespace(eventType  = eventTypes.DISCONNECTED,
                                                    data       = None,
                                                    connection = connection,
                                                    errorMsg   = None)
        for connection in conectionsToRemove:
            self.connections.remove(connection)
        return eventToReturn
    #---------------------------------------------------------------------
    def close(self, connection = None):
        if connection is None:
            self.__del__()
            self.connections = []
        else:
            conn, address = connection
            conn.close()
            self.connections.remove(connection)
    #---------------------------------------------------------------------
    def __del__(self):
        if 'side' in self.__dict__.keys():
            if self.side == 'server':
                self.listener.close()
        if 'connections' in self.__dict__.keys():
            for connection in self.connections:
                conn, address = connection
                conn.close()
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
                connection = self.connections[0]
        conn, addr = connection
        #TODO - Pendind send
        res = conn.sendall(data)
        logging.debug(f'{self.side}, sent {data}')
   
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
        return self.connections()
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