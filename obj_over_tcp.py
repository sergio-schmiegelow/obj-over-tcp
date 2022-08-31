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
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')

@unique
class eventTypes(Enum):
    ERROR           = -1
    CONNECTED       =  1
    DISCONNECTED    =  2
    DATA_RECEIVED   =  3
    OBJECT_RECEIVED =  4

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
class objOverTcp:
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

        self.side      = side
        self.address   = address
        self.port      = port
        self.decoder   = streamDecoder()
        self.sock      = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.side == 'server':
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.address, self.port))
            logging.info('Waiting for incomming connection')
            self.sock.listen()
            self.conn, self.addr = self.sock.accept()
            logging.info('Connected')
        else:
            logging.info('Waiting to connect')
            self.sock.connect((self.address, self.port))
            self.conn = self.sock
            logging.info('Connected')
    #---------------------------------------------------------------------
    def __del__(self):
        if 'side' in self.__dict__.keys():
            if self.side == 'server':
                self.conn.close()
            self.sock.close()
    #---------------------------------------------------------------------
    def send(self, obj):
        self.conn.sendall(encode(obj))
    #---------------------------------------------------------------------
    def receive(self, timeout = 0):
        if self.decoder.thereIsObject():
            return self.decoder.getObject()
        readList, writeList, errorList = select.select([self.conn], [], [self.conn], timeout)
        while len(readList) > 0:
            logging.debug(f'readList, writeList, errorList = {readList}, {writeList}, {errorList}')
            if len(readList) == 0: 
                break
            data = self.conn.recv(BUFFER_SIZE)
            self.decoder.insertBytes(data)
            readList, writeList, errorList = select.select([self.conn], [], [self.conn], 0)
        if self.decoder.thereIsObject():
            return self.decoder.getObject() 
        return None

#-------------------------------------------------------------------------
class asyncSimpleTcp:
    #---------------------------------------------------------------------
    def __init__(self, side, address, port, callback, userData = None):
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
 
        self.side         = side
        self.address      = address
        self.port         = port
        self.callback     = callback
        self.userData     = userData
        self.connections  = []
        self.running      = False
        if self.side == 'server':
            self.serverTask  = asyncio.create_task(self.serverCoroutine())
        else: #client
            self.clientTask  = asyncio.create_task(self.clientCoroutine())
    #---------------------------------------------------------------------
    async def clientConnectedCallback(self, reader, writer):
        print('clientConnectedCallback')
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
        print('DEBUG receiverCoroutine')
        while True:
            if self.isConnected():
                print('DEBUG receiverCoroutine, isConnected')
                try:
                    data = await reader.read(BUFFER_SIZE)
                except:
                    data = b''
                if len(data) == 0:
                    print('Disconnected')
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
        print(f'DEBUG - its a server')
        try:
            self.server = await asyncio.start_server(self.clientConnectedCallback, self.address, self.port)
        except Exception as e:
            self.server = None
            await self.callback(SimpleNamespace(eventType = eventTypes.ERROR,
                                                astObj     = self,
                                                data       = None,
                                                userData   = self.userData,
                                                connection = None,
                                                errorMsg   = e)) 
            return
        self.running = True    
        print(f'DEBUG - self.server = {self.server}')
        addrs = ', '.join(str(sock.getsockname()) for sock in self.server.sockets)
        print(f'Serving on {addrs}')
    #---------------------------------------------------------------------
    async def clientCoroutine(self):
        print(f'DEBUG - its a client')
        try:
            connection = await asyncio.open_connection(self.address, self.port)
        except Exception as e:
            await self.callback(SimpleNamespace(eventType  = eventTypes.ERROR,
                                                astObj     = self,
                                                object     = None,
                                                userData   = self.userData,
                                                connection = None,
                                                errorMsg   = e)) 
            return
        self.running = True
        print(f'DEBUG 20220830134109 - connection = {connection}')
        self.connections.append(connection)
        print("Client_connected")
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
    async def send(self, data, connection = None):
        if connection is None:
            if len(self.connections) == 0:
                logging.warning('Not connected')
                return
            else:
                reader, writer = self.connections[0]
        else:
            reader, writer = connection
        writer.write(data)
        await writer.drain()
#-------------------------------------------------------------------------
class asyncObjOverTcp(asyncSimpleTcp):
    #---------------------------------------------------------------------
    def __init__(self, side, address, port, userCallback, userData = None):
        super().__init__(side, address, port, self.innerCallback, userData)
        self.userCallback = userCallback
        self.decoder      = streamDecoder()
    #---------------------------------------------------------------------
    async def innerCallback(self, event):
        print('DEBUG - innerCallback')
        event.ootObj = self
        if event.eventType == eventTypes.DATA_RECEIVED:
            self.decoder.insertBytes(event.data)
            if self.decoder.thereIsObject():
                event.object = self.decoder.getObject()
                event.eventType = eventTypes.OBJECT_RECEIVED
                await self.userCallback(event)
        else:
            event.object = None
            await self.userCallback(event)
    #---------------------------------------------------------------------
    async def send(self, obj, connection = None):
        await super().send(encode(obj), connection)