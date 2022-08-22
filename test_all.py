import obj_over_tcp as oot
import pytest
MAX_SEGMENT_SIZE = 1500
#-------------------------------------------------------------------------
def test_object_creation():
    with pytest.raises(ValueError):
        cnxObj = oot.objOverTcp('xyz', '0.0.0.0', 10000)
    with pytest.raises(TypeError):
        cnxObj = oot.objOverTcp('server', 1, 10000)
    with pytest.raises(TypeError):
        cnxObj = oot.objOverTcp('server', '0.0.0.0', 'a')
    with pytest.raises(ValueError):
        cnxObj = oot.objOverTcp('xyz', '0.0.0.0', 99999)
#-------------------------------------------------------------------------        
def test_encode_decode():
    inList = ['12345', {'a':1, 'b':2}, {'aa':11, 'bb':22}, 12312, [str(x) for x in range(100000)]]
    buffer = b''
    for el in inList:
        buffer += oot.encode(el)
    sd = oot.streamDecoder()
    while len(buffer) > 0:
        segmentSize = min(MAX_SEGMENT_SIZE, len(buffer))
        segment = buffer[:segmentSize]
        buffer = buffer[segmentSize:]
        sd.insertBytes(segment)
    outList = []
    while True:
        el = sd.getObject()
        if el is not None:
            outList.append(el)
        else:
            break
    print(outList)
    assert(inList == outList)
#-------------------------------------------------------------------------    
def test_communication():
    pass
    
