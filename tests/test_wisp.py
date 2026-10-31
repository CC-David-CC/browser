import asyncio
import json
import tempfile
from pathlib import Path
import struct
import sys
import time
import unittest
from types import SimpleNamespace
from aiohttp import ClientSession, WSMsgType, web
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from relay.wisp import Relay
from relay.policy import DestinationPolicyLoader

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
        self.relay=Relay(policy_path=policy,origin='http://127.0.0.1',authenticate=authenticate,source=lambda r:'127.0.0.1',network_check=lambda ip:None,audit=self.audit.append,resolver=resolve,connector=connect)
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
            self.assertEqual(await self.read(ws),((4,1),b'\x48'));self.assertEqual(self.calls,[])
            await ws.send_bytes(self.pkt(1,2,dest('grainger.com')))
            await ws.send_bytes(self.pkt(2,2,b'hello'))
            messages=[await self.read(ws),await self.read(ws)]
            self.assertIn(((2,2),b'hello'),messages)
            self.assertEqual(self.calls,['grainger.com']);self.assertEqual(self.connections,[('1.1.1.1',443)])
        for _ in range(100):
            if not self.relay.users:break
            await asyncio.sleep(.01)
        self.assertFalse(self.relay.users)
        self.assertEqual(self.audit,[], 'Server audit must stay off by default')

    async def test_shared_stream_capacity_is_released_on_close(self):
        self.relay.max_streams=1;url=f'http://127.0.0.1:{self.port}/wisp/'
        headers={'Origin':'http://127.0.0.1','X-Test-Auth':'registered'}
        async with self.client.ws_connect(url,headers=headers) as a,self.client.ws_connect(url,headers=headers) as b:
            await self.read(a);await self.read(b);destination=bytes([1])+struct.pack('<H',443)+b'grainger.com'
            await a.send_bytes(self.pkt(1,1,destination));await a.send_bytes(self.pkt(2,1,b'first'))
            self.assertIn(((2,1),b'first'),[await self.read(a),await self.read(a)])
            await b.send_bytes(self.pkt(1,1,destination));self.assertEqual(await self.read(b),((4,1),b'\x49'))
            await a.send_bytes(self.pkt(4,1,b'\x01'));self.assertEqual((await self.read(a))[0],(4,1))
            await b.send_bytes(self.pkt(1,2,destination));await b.send_bytes(self.pkt(2,2,b'second'))
            self.assertIn(((2,2),b'second'),[await self.read(b),await self.read(b)])
        for _ in range(100):
            if not self.relay.active_streams:break
            await asyncio.sleep(.01)
        self.assertEqual(self.relay.active_streams,0)

    async def test_falls_back_to_other_validated_address(self):
        attempts=[]
        async def resolve(name,port):return ['2606:4700:4700::1111','1.1.1.1']
        async def connect(ip,port):
            attempts.append(ip)
            if ':' in ip:raise OSError('IPv6 unavailable')
            return await asyncio.open_connection('127.0.0.1',self.echo_port)
        self.relay.resolver=resolve;self.relay.connector=connect
        url=f'http://127.0.0.1:{self.port}/wisp/'
        async with self.client.ws_connect(url,headers={'Origin':'http://127.0.0.1','X-Test-Auth':'registered'}) as ws:
            await self.read(ws);await ws.send_bytes(self.pkt(1,2,bytes([1])+struct.pack('<H',443)+b'grainger.com'))
            await ws.send_bytes(self.pkt(2,2,b'fallback'))
            self.assertIn(((2,2),b'fallback'),[await self.read(ws),await self.read(ws)])
            self.assertEqual(attempts,['2606:4700:4700::1111','1.1.1.1'])

    async def test_dns_rebinding_and_mixed_answers_cannot_reach_private_addresses(self):
        # Each new stream performs a fresh check, and the connector receives the
        # vetted numeric address rather than a hostname it could resolve again.
        answers=iter((['1.1.1.1'],['127.0.0.1'],['2606:4700:4700::1111','::1'],['::ffff:127.0.0.1']))
        async def resolve(name,port):
            self.calls.append(name)
            return next(answers)
        self.relay.resolver=resolve
        url=f'http://127.0.0.1:{self.port}/wisp/'
        async with self.client.ws_connect(url,headers={'Origin':'http://127.0.0.1','X-Test-Auth':'registered'}) as ws:
            await self.read(ws);destination=bytes([1])+struct.pack('<H',443)+b'grainger.com'
            await ws.send_bytes(self.pkt(1,1,destination));await ws.send_bytes(self.pkt(2,1,b'public'))
            self.assertIn(((2,1),b'public'),[await self.read(ws),await self.read(ws)])
            for stream in (2,3,4):
                await ws.send_bytes(self.pkt(1,stream,destination))
                self.assertEqual(await self.read(ws),((4,stream),b'\x48'))
            self.assertEqual(self.calls,['grainger.com']*4)
            self.assertEqual(self.connections,[('1.1.1.1',443)])

    async def test_slow_connection_does_not_stall_other_streams(self):
        release=asyncio.Event()
        async def resolve(name,port):
            if name=='slow.example':await release.wait()
            return ['1.1.1.1']
        self.relay.resolver=resolve
        url=f'http://127.0.0.1:{self.port}/wisp/'
        async with self.client.ws_connect(url,headers={'Origin':'http://127.0.0.1','X-Test-Auth':'registered'}) as ws:
            await self.read(ws)
            def dest(name):return bytes([1])+struct.pack('<H',443)+name.encode()
            await ws.send_bytes(self.pkt(1,1,dest('slow.example')))
            await ws.send_bytes(self.pkt(2,1,b'queued'))
            await ws.send_bytes(self.pkt(1,2,dest('grainger.com')))
            await ws.send_bytes(self.pkt(2,2,b'fast'))
            fast=[await self.read(ws),await self.read(ws)]
            self.assertIn(((2,2),b'fast'),fast)
            release.set()
            slow=[await self.read(ws),await self.read(ws)]
            self.assertIn(((2,1),b'queued'),slow)
        for _ in range(100):
            if not self.relay.users:break
            await asyncio.sleep(.01)
        self.assertFalse(self.relay.users)

    async def test_disconnect_cancels_slow_connection_and_releases_capacity(self):
        started=asyncio.Event();cancelled=asyncio.Event()
        async def resolve(name,port):
            started.set()
            try:await asyncio.Event().wait()
            finally:cancelled.set()
        self.relay.resolver=resolve
        url=f'http://127.0.0.1:{self.port}/wisp/'
        ws=await self.client.ws_connect(url,headers={'Origin':'http://127.0.0.1','X-Test-Auth':'registered'})
        await self.read(ws)
        await ws.send_bytes(self.pkt(1,1,bytes([1])+struct.pack('<H',443)+b'slow.example'))
        await asyncio.wait_for(started.wait(),2)
        await ws.close()
        await asyncio.wait_for(cancelled.wait(),2)
        for _ in range(100):
            if not self.relay.users:break
            await asyncio.sleep(.01)
        self.assertFalse(self.relay.users)

    async def test_renewed_lease_keeps_socket_and_revocation_closes_it(self):
        principal=SimpleNamespace(kind='registered',sub='user:test',deadline=time.time()+0.5)
        async def authenticate(request):return principal
        self.relay.authenticate=authenticate
        url=f'http://127.0.0.1:{self.port}/wisp/'
        async with self.client.ws_connect(url,headers={'Origin':'http://127.0.0.1'}) as ws:
            await self.read(ws)
            await asyncio.sleep(0.2);principal.deadline=time.time()+2
            await asyncio.sleep(0.5)
            await ws.send_bytes(self.pkt(1,1,bytes([1])+struct.pack('<H',443)+b'grainger.com'))
            await ws.send_bytes(self.pkt(2,1,b'after-renewal'))
            self.assertIn(((2,1),b'after-renewal'),[await self.read(ws),await self.read(ws)])
            principal.deadline=0
            msg=await asyncio.wait_for(ws.receive(),2)
            self.assertIn(msg.type,(WSMsgType.CLOSE,WSMsgType.CLOSED,WSMsgType.CLOSING))

    async def test_shared_outgoing_ip_block_is_checked_before_connect(self):
        def deny(ip):raise ValueError('blocked')
        self.relay.network_check=deny
        url=f'http://127.0.0.1:{self.port}/wisp/'
        async with self.client.ws_connect(url,headers={'Origin':'http://127.0.0.1','X-Test-Auth':'registered'}) as ws:
            await self.read(ws)
            await ws.send_bytes(self.pkt(1,4,bytes([1])+struct.pack('<H',443)+b'grainger.com'))
            self.assertEqual((await self.read(ws))[0],(4,4))
            self.assertEqual(self.calls,['grainger.com']);self.assertEqual(self.connections,[])

    async def test_new_domain_block_stops_an_existing_stream(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'policy.json';value=json.loads(self.relay.policy_path.read_text());path.write_text(json.dumps(value))
            self.relay.policy_path=path;self.relay.policies=DestinationPolicyLoader(path)
            url=f'http://127.0.0.1:{self.port}/wisp/'
            async with self.client.ws_connect(url,headers={'Origin':'http://127.0.0.1','X-Test-Auth':'registered'}) as ws:
                await self.read(ws)
                await ws.send_bytes(self.pkt(1,2,bytes([1])+struct.pack('<H',443)+b'grainger.com'))
                await ws.send_bytes(self.pkt(2,2,b'before'))
                self.assertIn(((2,2),b'before'),[await self.read(ws),await self.read(ws)])
                value['blacklist'].append('grainger.com');new=path.with_suffix('.new');new.write_text(json.dumps(value));new.replace(path)
                await ws.send_bytes(self.pkt(2,2,b'after'))
                self.assertEqual(await self.read(ws),((4,2),b'\x48'))

    async def test_new_outgoing_block_stops_an_existing_stream(self):
        state={'blocked':False}
        def check(ip):
            if state['blocked']:raise ValueError('blocked')
        self.relay.network_check=check
        url=f'http://127.0.0.1:{self.port}/wisp/'
        async with self.client.ws_connect(url,headers={'Origin':'http://127.0.0.1','X-Test-Auth':'registered'}) as ws:
            await self.read(ws)
            await ws.send_bytes(self.pkt(1,2,bytes([1])+struct.pack('<H',443)+b'grainger.com'))
            await ws.send_bytes(self.pkt(2,2,b'before'))
            first=[await self.read(ws),await self.read(ws)];self.assertIn(((2,2),b'before'),first)
            state['blocked']=True
            await ws.send_bytes(self.pkt(2,2,b'after'))
            self.assertEqual(await self.read(ws),((4,2),b'\x48'))

if __name__=='__main__':unittest.main()
