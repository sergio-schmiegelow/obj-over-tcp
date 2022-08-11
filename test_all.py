import obj_over_tcp as oot
import pytest
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
    pass 