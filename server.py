import obj_over_tcp as oot
import time

myCnx = oot.objOverTcp('server', '0.0.0.0', 10000)
obj = myCnx.receive()
print(obj)
myDict = {'aa':11, 'bb':22}
myCnx.send(myDict)
