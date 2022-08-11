import obj_over_tcp as oot
import time

myCnx = oot.objOverTcp('client', '127.0.0.1', 10000)
myDict = {'a':1, 'b':2}
print("DEBUG 1")
myCnx.send(myDict)
print("DEBUG 2")
obj = myCnx.receive(1)
print("DEBUG 3")
while obj is None:
    print("DEBUG 4")
    obj = myCnx.receive(1)
    print("DEBUG 5")
print("DEBUG 6")
print(obj)
