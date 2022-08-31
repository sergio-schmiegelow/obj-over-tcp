import asyncio
from pydoc import cli
import obj_over_tcp as oot
import pytest
#-------------------------------------------------------------------------
async def serverCoro():
    serverResList = []
    #---------------------------------------------------------------------
    async def callback(event):
        print(f'Server callback, eventType = {event.eventType}, ootObj = {event.ootObj}, userData = {event.userData}')
        if event.eventType == oot.CONNECTED:
            print(f'Connected')
            print(f'connection = {event.connection}')
        elif event.eventType == oot.OBJECT_RECEIVED:
            print(f'Connected')
            print(f'connection = {event.connection}')
            print(f'object = {event.object}')
            await event.ootObj.send('answer', event.connection)
            serverResList.append(event.object)
        elif event.eventType == oot.ERROR:
            print(f'Error')
            print(f'connection = {event.connection}')
            print(f'errorMsg = {event.errorMsg}')
        else:
            raise Exception('Unknown eventType')
    #---------------------------------------------------------------------
    myOOT = oot.asyncObjOverTcp('server', '0.0.0.0', 10000, callback, 'server user data')
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
    async def callback(event):
        print(f'Client callback, eventType = {event.eventType}, ootObj = {event.ootObj}, userData = {event.userData}')
        if event.eventType == oot.CONNECTED:
            print(f'Connected')
            print(f'connection = {event.connection}')
            await event.ootObj.send('request', event.connection)
        elif event.eventType == oot.OBJECT_RECEIVED:
            print(f'Connected')
            print(f'connection = {event.connection}')
            print(f'object = {event.object}')
            clientResList.append(event.object)
        elif event.eventType == oot.ERROR:
            print(f'Error')
            print(f'connection = {event.connection}')
            print(f'errorMsg = {event.errorMsg}')
        else:
            raise Exception('Unknown eventType')
    #---------------------------------------------------------------------
    myOOT = oot.asyncObjOverTcp('client', '127.0.0.1', 10000, callback)
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
    assert (serverRes, clientRes) == ('request', 'answer')
#-------------------------------------------------------------------------
if __name__ == '__main__':
    asyncio.run(test_client_server())