"""Bounded Wisp v1 TCP transport. Authentication must be supplied by the host.

No listener is started here. The caller must authenticate registered users
before upgrading, provide trustworthy source attribution, and configure its
own protected policy path. This module has no anonymous/default authenticator.
"""
import asyncio
import ipaddress
import socket
import struct
import time
from aiohttp import web, WSMsgType
from .policy import DestinationPolicyLoader, PolicyDenied

MAX_FRAME = 65536
WINDOW = 8
MAX_QUEUED_BYTES = 512 * 1024
CONNECT_TIMEOUT = 10
IDLE_TIMEOUT = 120
HOST_BLOCKED = 0x48  # Wisp's standard server-side policy denial reason.
CONNECTION_THROTTLED = 0x49

class ConnectionLimit(Exception):
    pass

class Relay:
    def __init__(self, *, policy_path, origin, authenticate, source, network_check, audit=None, resolver=None, connector=None, max_streams=1024):
        if not callable(authenticate) or not callable(source) or not callable(network_check):
            raise ValueError('Authenticated identity, trusted source and outbound access check are required')
        self.policy_path, self.origin = policy_path, origin
        self.authenticate, self.source = authenticate, source
        self.network_check=network_check
        self.resolver = resolver or self._resolve
        self.connector = connector or self._connect
        if type(max_streams) is not int or not 1<=max_streams<=4096:raise ValueError('Bounded shared stream capacity required')
        self.users = {};self.active_streams=0;self.max_streams=max_streams
        # Fail early for invalid configuration; re-read for each new stream.
        self.policies=DestinationPolicyLoader(policy_path);policy=self.policies.current()
        if policy.server_audit_enabled and not callable(audit):raise ValueError('Enabled server audit needs a protected ledger')
        self.audit_enabled=policy.server_audit_enabled
        self.audit=audit if self.audit_enabled else lambda _event:None

    def check_stream(self,name,port,address):
        policy=self.policies.current()
        if policy.server_audit_enabled!=self.audit_enabled:raise PolicyDenied('Audit mode changed; restart relay')
        policy.check_hostname(name,port);self.check_network(address)

    def check_network(self,address):
        try:self.network_check(address)
        except ValueError as error:raise PolicyDenied('Destination blocked by network policy') from error

    async def _resolve(self, name, port):
        loop = asyncio.get_running_loop()
        entries = await loop.getaddrinfo(name, port, type=socket.SOCK_STREAM)
        return [entry[4][0] for entry in entries]

    async def _connect(self, address, port):
        family = socket.AF_INET6 if ipaddress.ip_address(address).version == 6 else socket.AF_INET
        return await asyncio.open_connection(address, port, family=family, flags=socket.AI_NUMERICHOST)

    async def handle(self, request):
        if request.method != 'GET' or request.headers.get('Origin') != self.origin:
            raise web.HTTPForbidden()
        principal = await self.authenticate(request)
        if not principal or principal.kind != 'registered' or principal.deadline <= time.time():
            raise web.HTTPUnauthorized()
        peer = self.source(request)
        if not isinstance(peer, str) or not peer:
            raise web.HTTPForbidden()
        ws = web.WebSocketResponse(max_msg_size=MAX_FRAME+5, heartbeat=30, compress=False)
        await ws.prepare(request)
        streams = {}
        pending = {}
        async def packet(kind, stream_id, data=b''):
            if not ws.closed: await ws.send_bytes(struct.pack('<BI', kind, stream_id)+data)
        async def finish(stream_id, reason=1):
            entry = streams.pop(stream_id, None)
            if not entry: return
            self.users[principal.sub] -= 1;self.active_streams -= 1
            if not self.users[principal.sub]: del self.users[principal.sub]
            others=[task for task in entry['tasks'] if task is not asyncio.current_task()]
            for task in others:task.cancel()
            writer = entry.get('writer')
            if writer:
                writer.close()
                try: await asyncio.wait_for(writer.wait_closed(), 2)
                except (Exception, asyncio.CancelledError): pass
            if others:await asyncio.gather(*others,return_exceptions=True)
            try:self.audit({'subject':principal.sub,'source':peer,'destination':entry['name'],'port':entry['port'],'sentBytes':entry['sent'],'receivedBytes':entry['received'],'event':'closed'})
            except Exception:await ws.close(code=1011,message=b'Audit unavailable')
            await packet(4,stream_id,bytes([reason]))
        async def pump_out(stream_id, entry):
            reason=1
            try:
                while True:
                    data = await asyncio.wait_for(entry['reader'].read(MAX_FRAME), IDLE_TIMEOUT)
                    if not data: break
                    self.check_stream(entry['name'],entry['port'],entry['address'])
                    entry['received'] += len(data)
                    await packet(2,stream_id,data)
            except PolicyDenied:reason=HOST_BLOCKED
            except Exception:reason=3
            finally: await finish(stream_id,reason)
        async def pump_in(stream_id, entry):
            try:
                while True:
                    data = await asyncio.wait_for(entry['queue'].get(), IDLE_TIMEOUT)
                    entry['queued'] -= len(data)
                    self.check_stream(entry['name'],entry['port'],entry['address'])
                    entry['writer'].write(data)
                    await asyncio.wait_for(entry['writer'].drain(), IDLE_TIMEOUT)
                    entry['sent'] += len(data)
                    await packet(3,stream_id,struct.pack('<I',WINDOW-entry['queue'].qsize()))
            except PolicyDenied:
                await finish(stream_id,HOST_BLOCKED)
            except Exception:
                await finish(stream_id,3)
        async def connect(stream_id, payload):
            if stream_id == 0 or stream_id in streams or len(payload)<4 or payload[0]!=1:
                await packet(4,stream_id,b'\x03');return
            port=struct.unpack_from('<H',payload,1)[0]
            reserved=False
            try:
                raw=payload[3:].decode('utf-8','strict');policy=self.policies.current()
                if policy.server_audit_enabled!=self.audit_enabled:raise PolicyDenied('Audit mode changed; restart relay')
                name=policy.check_hostname(raw,port)
                if self.users.get(principal.sub,0)>=policy.max_connections_per_user or self.active_streams>=self.max_streams:raise ConnectionLimit('Connection limit')
                self.users[principal.sub]=self.users.get(principal.sub,0)+1;self.active_streams+=1;reserved=True
                addresses=policy.check_addresses(await asyncio.wait_for(self.resolver(name,port),CONNECT_TIMEOUT))
                if len(addresses)>32:raise PolicyDenied('Too many resolved addresses')
                for address in addresses:self.check_network(address)
                # Some hosts publish IPv6 even when this relay has no IPv6 route.
                # Try each already-vetted address with a bounded total deadline;
                # never ask DNS again during connection establishment.
                async with asyncio.timeout(CONNECT_TIMEOUT):
                    for address in addresses:
                        try:
                            reader,writer=await asyncio.wait_for(self.connector(address,port),3)
                            break
                        except (OSError,TimeoutError):continue
                    else:raise OSError('No validated address was reachable')
            except Exception as error:
                if reserved:
                    self.users[principal.sub]-=1;self.active_streams-=1
                    if not self.users[principal.sub]:del self.users[principal.sub]
                try:self.audit({'subject':principal.sub,'source':peer,'destination':raw if 'raw' in locals() else '', 'port':port,'event':'denied'})
                except Exception:await ws.close(code=1011,message=b'Audit unavailable');return
                reason=HOST_BLOCKED if isinstance(error,PolicyDenied) else CONNECTION_THROTTLED if isinstance(error,ConnectionLimit) else 3
                await packet(4,stream_id,bytes([reason]));return
            except asyncio.CancelledError:
                if reserved:
                    self.users[principal.sub]-=1;self.active_streams-=1
                    if not self.users[principal.sub]:del self.users[principal.sub]
                raise
            entry={'name':name,'port':port,'address':address,'reader':reader,'writer':writer,'queue':asyncio.Queue(maxsize=WINDOW),'queued':0,'sent':0,'received':0,'tasks':[]}
            streams[stream_id]=entry
            waiting=pending.pop(stream_id, None)
            if waiting:
                for data in waiting['buffer']:
                    entry['queued'] += len(data);entry['queue'].put_nowait(data)
            try:self.audit({'subject':principal.sub,'source':peer,'destination':name,'port':port,'event':'opened'})
            except Exception:
                await finish(stream_id,3);await ws.close(code=1011,message=b'Audit unavailable');return
            entry['tasks']=[asyncio.create_task(pump_out(stream_id,entry)),asyncio.create_task(pump_in(stream_id,entry))]
        await packet(3,0,struct.pack('<I',WINDOW))
        async def expire_lease():
            while not ws.closed:
                remaining=principal.deadline-time.time()
                if remaining<=0:
                    await ws.close(code=1008,message=b'Relay session expired');return
                # The authenticated host may renew the same bound lease. Polling
                # at most once per second also makes explicit revocation prompt.
                await asyncio.sleep(min(remaining,1))
        expiry=asyncio.create_task(expire_lease())
        try:
            async for message in ws:
                if principal.deadline <= time.time(): break
                if message.type != WSMsgType.BINARY or len(message.data)<5: break
                kind, stream_id = struct.unpack_from('<BI',message.data)
                payload = message.data[5:]
                if kind==1:
                    if stream_id==0 or stream_id in streams or stream_id in pending or len(pending)>=128:
                        await packet(4,stream_id,b'\x03');continue
                    waiting={'buffer':[],'queued':0,'task':None}
                    pending[stream_id]=waiting
                    async def connecting(sid, data, state):
                        try:await connect(sid,data)
                        finally:
                            if pending.get(sid) is state:pending.pop(sid,None)
                    waiting['task']=asyncio.create_task(connecting(stream_id,payload,waiting))
                elif kind==2:
                    entry=streams.get(stream_id)
                    if not entry and payload:
                        waiting=pending.get(stream_id)
                        if waiting:
                            if len(waiting['buffer'])>=WINDOW or waiting['queued']+len(payload)>MAX_QUEUED_BYTES:
                                pending.pop(stream_id,None);waiting['task'].cancel()
                                await asyncio.gather(waiting['task'],return_exceptions=True)
                                await packet(4,stream_id,b'\x03')
                            else:
                                waiting['buffer'].append(payload);waiting['queued']+=len(payload)
                        continue
                    if not entry or not payload:continue
                    if entry['queue'].full() or entry['queued']+len(payload)>MAX_QUEUED_BYTES:
                        await finish(stream_id,3);continue
                    entry['queued'] += len(payload);entry['queue'].put_nowait(payload)
                elif kind==4:
                    waiting=pending.pop(stream_id,None)
                    if waiting:
                        waiting['task'].cancel();await asyncio.gather(waiting['task'],return_exceptions=True)
                    await finish(stream_id)
                else: break
        finally:
            expiry.cancel()
            tasks=[item['task'] for item in pending.values()]
            pending.clear()
            for task in tasks:task.cancel()
            if tasks:await asyncio.gather(*tasks,return_exceptions=True)
            for stream_id in list(streams): await finish(stream_id)
            await asyncio.gather(expiry,return_exceptions=True)
            await ws.close()
        return ws
