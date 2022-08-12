import logging
import pickle
import select
import socket


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