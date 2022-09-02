import asyncio
import obj_over_tcp as oot

async def callback(event):
    if event.eventType == oot.eventTypes.CONNECTED:
        await event.ootObj.send('my message') #can be any Python object
    if event.eventType == oot.eventTypes.OBJECT_RECEIVED:
        print(f'Echo received:{event.object}')
        await event.ootObj.close()

async def main():
    myOOT = oot.asyncObjOverTcp('client', '127.0.0.1', 10000, callback)
    while myOOT.isRunning():
        #Other loop code here
        await asyncio.sleep(0.1)

asyncio.run(main())