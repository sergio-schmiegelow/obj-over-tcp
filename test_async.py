import asyncio
from pydoc import cli
import obj_over_tcp as oot
import pytest
#-------------------------------------------------------------------------
async def serverCoro():
    serverResList = []
    #---------------------------------------------------------------------
    async def cnxCallback(OOT, connection):
        print(f'(server)cnxCallback')
    #---------------------------------------------------------------------    
    async def objRxCallback(OOT, connection, obj):
        print(f'(server)objRxCallback({obj})')
        await OOT.send('answer', connection)
        serverResList.append(obj)
        print(f'(server)end of objRxCallback')
    #---------------------------------------------------------------------
    myOOT = oot.asyncObjOverTcp('server', '0.0.0.0', 10000, cnxCallback, objRxCallback)
    while True:
        print('serverCoro loop')
        await asyncio.sleep(0.1)
        print(f'serverResList = {serverResList}')
        if len(serverResList) > 0:
            await myOOT.close()
            break
    return serverResList[0]
#-------------------------------------------------------------------------
async def clientCoro():
    clientResList = []
    #---------------------------------------------------------------------
    async def cnxCallback(OOT, connection):
        print(f'(client)cnxCallback')
        await OOT.send('request', connection)
    #---------------------------------------------------------------------    
    async def objRxCallback(OOT, connection, obj):
        print(f'(client)objRxCallback({obj})')
        clientResList.append(obj)
        print(f'(client)end of objRxCallback')
    #---------------------------------------------------------------------
    myOOT = oot.asyncObjOverTcp('client', '127.0.0.1', 10000, cnxCallback, objRxCallback)
    while True:
        print('clientCoro loop')
        await asyncio.sleep(0.1)
        print(f'clientResList = {clientResList}')
        if len(clientResList) > 0:
            await myOOT.close()
            break
    return clientResList[0]
#-------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_client_server():        
    st = asyncio.create_task(serverCoro())
    await asyncio.sleep(0.1)
    ct = asyncio.create_task(clientCoro())
    serverRes = await(st)
    clientRes = await(ct)
    print(f'serverRes = {serverRes}')
    print(f'clientRes = {clientRes}')
    #assert (serverRes, clientRes) == ('request', 'answer')
#-------------------------------------------------------------------------
if __name__ == '__main__':
    asyncio.run(test_client_server())