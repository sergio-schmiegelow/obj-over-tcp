import obj_over_tcp as oot
import time

myCnx = oot.objOverTcp('server', '0.0.0.0', 10000)
obj = myCnx.receive(1)
while obj is None:
    obj = myCnx.receive(1)
print(obj)
myDict = {'aa':11, 'bb':22}
myCnx.send(myDict)
time.sleep(1)