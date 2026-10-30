import asyncio
from pathlib import Path
import struct
import sys
import time
import unittest
from types import SimpleNamespace
from aiohttp import ClientSession, WSMsgType, web
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from relay.wisp import Relay

class WispRelayTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.calls=[];self.connections=[];self.audit=[]
        async def echo(reader,writer):
            try:
                while data:=await reader.read(65536):writer.write(data);await writer.drain()
            finally:writer.close();await writer.wait_closed()
        self.echo=await asyncio.start_server(echo,'127.0.0.1',0)
        self.echo_port=self.echo.sockets[0].getsockname()[1]
        async def authenticate(request):
            return None if request.headers.get('X-Test-Auth')!='registered' else SimpleNamespace(kind='registered',sub='user:test',deadline=time.time()+30)
        async def resolve(name,port):self.calls.append(name);return ['1.1.1.1']
        async def connect(ip,port):self.connections.append((ip,port));return await asyncio.open_connection('127.0.0.1',self.echo_port)
        policy=Path(__file__).resolve().parents[1]/'relay/policy.json'
        self.relay=Relay(policy_path=policy,origin='http://127.0.0.1',authenticate=authenticate,source=lambda r:'127.0.0.1',audit=self.audit.append,resolver=resolve,connector=connect)
        app=web.Application();app.router.add_get('/wisp/',self.relay.handle);self.runner=web.AppRunner(app);await self.runner.setup();site=web.TCPSite(self.runner,'127.0.0.1',0);await site.start();self.port=site._server.sockets[0].getsockname()[1]
        self.client=ClientSession()

    async def asyncTearDown(self):
        await self.client.close();await self.runner.cleanup();self.echo.close();await self.echo.wait_closed()

    def pkt(self,kind,stream,payload=b''):return struct.pack('<BI',kind,stream)+payload
    async def read(self,ws):
        msg=await asyncio.wait_for(ws.receive(),5);self.assertEqual(msg.type,WSMsgType.BINARY);return struct.unpack_from('<BI',msg.data),msg.data[5:]

    async def test_rejects_unauthenticated_or_wrong_origin(self):
        url=f'http://127.0.0.1:{self.port}/wisp/'
        async with self.client.get(url,headers={'Origin':'http://127.0.0.1'}) as r:self.assertEqual(r.status,401)
        async with self.client.get(url,headers={'Origin':'http://bad','X-Test-Auth':'registered'}) as r:self.assertEqual(r.status,403)

    async def test_blocked_before_dns_allowed_connects_to_validated_address(self):
        url=f'http://127.0.0.1:{self.port}/wisp/'
        async with self.client.ws_connect(url,headers={'Origin':'http://127.0.0.1','X-Test-Auth':'registered'}) as ws:
            self.assertEqual((await self.read(ws))[0],(3,0))
            def dest(name):return bytes([1])+struct.pack('<H',443)+name.encode()
            await ws.send_bytes(self.pkt(1,1,dest('www.youtube.com')))
            self.assertEqual((await self.read(ws))[0],(4,1));self.assertEqual(self.calls,[])
            await ws.send_bytes(self.pkt(1,2,dest('grainger.com')))
            await ws.send_bytes(self.pkt(2,2,b'hello'))
            messages=[await self.read(ws),await self.read(ws)]
            self.assertIn(((2,2),b'hello'),messages)
            self.assertEqual(self.calls,['grainger.com']);self.assertEqual(self.connections,[('1.1.1.1',443)])
        self.assertFalse(self.relay.users)
        self.assertEqual(self.audit,[], 'Server audit must stay off by default')

if __name__=='__main__':unittest.main()
