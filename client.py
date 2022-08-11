import obj_over_tcp as oot
import time

myCnx = oot.objOverTcp('client', '127.0.0.1', 10000)
myDict = {'a':1, 'b':2}
myCnx.send(myDict)
obj = myCnx.receive()
print(obj)
