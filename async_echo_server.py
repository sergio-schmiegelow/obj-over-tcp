import asyncio
import obj_over_tcp as oot

async def callback(event):
    if event.eventType == oot.eventTypes.OBJECT_RECEIVED:
        print(f'Object received:{event.object}')
        await event.ootObj.send(event.object)
    elif event.eventType == oot.eventTypes.ERROR:
        print(f'ERROR: {event.errorMsg}')
        quit()

async def main():
    myOOT = oot.asyncObjOverTcp('server', '0.0.0.0', 10000, callback)
    while True:
        #Other loop code here
        await asyncio.sleep(0.1)

asyncio.run(main())