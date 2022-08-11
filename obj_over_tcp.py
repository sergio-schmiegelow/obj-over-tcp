import socket
import logging
import pickle

BUFFER_SIZE = 65536
logging.basicConfig(level=logging.INFO)
#-------------------------------------------------------------------------
class objRebuilder:
    def __init__(self):
        self.objSize = None
        self.objBuilder = b''
        self.objsList = []
    #-------------------------------------------------------------------------
    def insertBytes(self, data):
        self.objBuilder += data
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
        self.rxObjSize = None
        self.rxBuffer  = b''
        self.sock      = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.side == 'server':
            #self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.address, self.port))
            logging.info('Waiting for incomming connection')
            self.sock.listen()
            self.conn, self.addr = self.sock.accept()
            logging.info('Connected')
        else:
            logging.info('Waiting to connect')
            #self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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
        pklObj = pickle.dumps(obj)
        self.conn.sendall(pklObj)
    #---------------------------------------------------------------------
    def receive(self):
        pklObj = self.conn.recv(BUFFER_SIZE)
        print(f'len(pklObj) = {len(pklObj)}')
        print(f'type(pklObj = {type(pklObj)}')
        obj = pickle.loads(pklObj)
        return obj
