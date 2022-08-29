import asyncio
import obj_over_tcp as oot
#-------------------------------------------------------------------------
async def serverCoro():
    serverResList = []
    #---------------------------------------------------------------------
    async def cnxCallback(OOT):
        print(f'(server)cnxCallback')
    #---------------------------------------------------------------------    
    async def objRxCallback(OOT, obj):
        print(f'(server)objRxCallback({obj})')
        await OOT.send('answer')
        serverResList.append(obj)
        print(f'(server)end of objRxCallback')
    #---------------------------------------------------------------------
    myOOT = oot.asyncObjOverTcp('server', '0.0.0.0', 10000, cnxCallback, objRxCallback)
    while True:
        print('serverCoro loop')
        await asyncio.sleep(1)
        print(f'serverResList = {serverResList}')
        if len(serverResList) > 0:
            return serverResList[0]
#-------------------------------------------------------------------------
async def clientCoro():
    clientResList = []
    #---------------------------------------------------------------------
    async def cnxCallback(OOT):
        print(f'(client)cnxCallback')
        await OOT.send('request')
    #---------------------------------------------------------------------    
    async def objRxCallback(OOT, obj):
        print(f'(client)objRxCallback({obj})')
        clientResList.append(obj)
        print(f'(client)end of objRxCallback')
    #---------------------------------------------------------------------
    myOOT = oot.asyncObjOverTcp('client', '127.0.0.1', 10000, cnxCallback, objRxCallback)
    while True:
        print('clientCoro loop')
        await asyncio.sleep(1)
        print(f'clientResList = {clientResList}')
        if len(clientResList) > 0:
            return clientResList[0]
#-------------------------------------------------------------------------
async def test_client_server():        
    st = asyncio.create_task(serverCoro())
    await asyncio.sleep(1)
    ct = asyncio.create_task(clientCoro())
    serverRes = await(st)
    clientRes = await(ct)
    print(f'serverRes = {serverRes}')
    print(f'clientRes = {clientRes}')
#-------------------------------------------------------------------------
asyncio.run(test_client_server(), debug = True)

