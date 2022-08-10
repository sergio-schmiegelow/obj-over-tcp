import obj_over_tcp as oot

myCnx = oot.objOverTcp('server', '0.0.0.0', 10000)
obj = myCnx.receive()
print(obj)
