import asyncio
from csv import reader
import logging
import pickle
import select
import socket


SELECT_TIME = 0.1
BUFFER_SIZE = 2048
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')

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
class asyncObjOverTcp:
    #---------------------------------------------------------------------
    def __init__(self, side, address, port, cnxCallback, objCallback):
        if side not in ['server', 'client']:
            raise ValueError("The side attribute must be 'server' or 'client'")
        if type(address) is not str:
            raise TypeError('The address attribute must be str')
        if type(port) is not int:
            raise TypeError('The port attribute must be int')
        if not 0 < port < 65535:
            raise ValueError('The port attribute must be a int between 0 and 65535')
        if not callable(cnxCallback):
            raise TypeError('The cnxCallback attribute must callable')
        if not callable(objCallback):
            raise TypeError('The objCallback attribute must callable')

        self.side         = side
        self.address      = address
        self.port         = port
        self.cnxCallback  = cnxCallback
        self.objCallback  = objCallback
        self.decoder      = streamDecoder()
        self.connections  = []
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
        print(f'DEBUG - self.cnxCallback = {self.cnxCallback}')
        await self.cnxCallback(self, connection)
        #TODO Tratar múltiplas conexões
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
                    self.connections = []
                    #TODO tratar múltiplas conexões
                    print('Disconnected')
                    #TODO tratar desconexão
                    break
                print(f'DEBUG - data = {data}')
                self.decoder.insertBytes(data)
                if self.decoder.thereIsObject():
                   await self.objCallback(self, connection, self.decoder.getObject())
    #---------------------------------------------------------------------
    async def serverCoroutine(self):
        print(f'DEBUG - its a server')
        self.server = await asyncio.start_server(self.clientConnectedCallback, self.address, self.port)
        print(f'DEBUG - self.server = {self.server}')
        addrs = ', '.join(str(sock.getsockname()) for sock in self.server.sockets)
        print(f'Serving on {addrs}')
    #---------------------------------------------------------------------
    async def clientCoroutine(self):
        print(f'DEBUG - its a client')
        connection = await asyncio.open_connection(self.address, self.port)
        self.connections.append(connection)
        print("Client_connected")
        self.receiverTask  = asyncio.create_task(self.receiverCoroutine(connection))
        await self.cnxCallback(self, connection)
        await self.receiverTask 
        #TODO tratar falha de conexão
    '''
    #---------------------------------------------------------------------
    def __del__(self):
        #TODO Implementar
        if 'side' in self.__dict__.keys():
            if self.side == 'server':
                self.conn.close()
            self.writer.close()
            await self.writer.wait_closed()
        self.conn = None
    #---------------------------------------------------------------------
    '''
    async def send(self, obj, connection = None):
        if connection is None:
            if len(self.connections) == 0:
                logging.warning('Not connected')
                return
            else:
                reader, writer = self.connections[0]
        else:
            reader, writer = connection
        print(f'DEBUG - asyncObjOverTcp.send({obj})')
        print(f'DEBUG - asyncObjOverTcp.send({obj}) - isConnected')
        writer.write(encode(obj))
        await writer.drain()
        print(f'{obj} was sent')
           
    