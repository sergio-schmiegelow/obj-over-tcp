import obj_over_tcp as oot
import pytest

def test_object_creation():
    try:
        cnxObj = oot.objOverTcp('client', '0.0.0.0', 10000)
    except:
        pytest.fail('Unexpected error on client creation')
    try:
        cnxObj = oot.objOverTcp('server', '0.0.0.0', 10000)
    except:
        pytest.fail('Unexpected error on server creation')
    with pytest.raises(ValueError):
        cnxObj = oot.objOverTcp('xyz', '0.0.0.0', 10000)
    with pytest.raises(TypeError):
        cnxObj = oot.objOverTcp('server', 1, 10000)
    with pytest.raises(TypeError):
        cnxObj = oot.objOverTcp('server', '0.0.0.0', 'a')
    with pytest.raises(ValueError):
        cnxObj = oot.objOverTcp('xyz', '0.0.0.0', 99999)
