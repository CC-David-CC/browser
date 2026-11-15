#!/usr/bin/env python3
"""Exercise audited URL downloads through the real HTTP adapter and ledger."""
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace

from aiohttp import ClientSession,web
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'server'),str(ROOT),str(ROOT/'tests')]
from browser_service.http import BrowserHTTP
from relay.audit import AuditLedger
from relay.download import Downloader
from relay.policy import PolicyDenied,DownloadTooLarge,hostname

class FixturePolicy:
    server_audit_enabled=True
    def check_hostname(self,host,port):
        name=hostname(host)
        if name=='blocked.example':raise PolicyDenied('Blocked fixture')
        return name
    def check_addresses(self,values):return tuple(values)  # loopback fixture only

class Session:
    def principal(self,*_args):return SimpleNamespace(sub='user:test',deadline=time.time()+30)

class AuditHTTP(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='codi-audit-http-');self.addCleanup(self.temp.cleanup)
        self.ledger=AuditLedger(Path(self.temp.name)/'events.sqlite3',Ed25519PrivateKey.generate())
        async def target(request):
            if request.path=='/redirect':raise web.HTTPFound('/secret-file')
            if request.path=='/blocked':raise web.HTTPFound(f'http://blocked.example:{self.target_port}/secret-file')
            return web.Response(body=b'private file contents')
        app=web.Application();app.router.add_get('/{tail:.*}',target);self.target=web.AppRunner(app);await self.target.setup();site=web.TCPSite(self.target,'127.0.0.1',0);await site.start();self.target_port=site._server.sockets[0].getsockname()[1]
        async def resolve(_name,_port):return ['127.0.0.1']
        relay=SimpleNamespace(audit_enabled=True,audit=self.ledger.append,source=lambda _request:'198.51.100.6',policy_path='fixture',resolver=resolve,network_check=lambda _ip:None,check_stream=lambda *_args:None)
        downloader=Downloader(relay,load_policy=lambda _:FixturePolicy())
        adapter=BrowserHTTP(Session(),relay,origin='http://127.0.0.1',secure_cookie=False,downloader=downloader)
        async def body(_request,_keys):return {'url':f'http://allowed.example:{self.target_port}/redirect'}
        self.adapter=adapter;adapter.body=body;adapter.identifier=lambda _request:'test';adapter.secret=lambda _request:'test'
        app=web.Application();app.router.add_post('/download',adapter.download);self.front=web.AppRunner(app);await self.front.setup();site=web.TCPSite(self.front,'127.0.0.1',0);await site.start();self.front_port=site._server.sockets[0].getsockname()[1]
    async def asyncTearDown(self):await self.front.cleanup();await self.target.cleanup()

    async def test_size_error_is_clear_but_other_policy_failures_stay_generic(self):
        async def too_large(*_args,**_kwargs):raise DownloadTooLarge('sensitive internal detail')
        async def denied(*_args,**_kwargs):raise PolicyDenied('sensitive internal detail')
        async with ClientSession() as client:
            self.adapter.downloader.fetch=too_large
            async with client.post(f'http://127.0.0.1:{self.front_port}/download') as response:
                self.assertEqual(response.status,413);self.assertEqual((await response.json())['error'],'Download is larger than 128 MiB.')
            self.adapter.downloader.fetch=denied
            async with client.post(f'http://127.0.0.1:{self.front_port}/download') as response:
                self.assertEqual(response.status,403);self.assertNotIn('sensitive',(await response.json())['error'])

    async def test_signed_metadata_covers_redirect_and_never_contains_file_or_path(self):
        async with ClientSession() as client:
            async with client.post(f'http://127.0.0.1:{self.front_port}/download') as response:
                self.assertEqual(response.status,200);self.assertEqual(await response.read(),b'private file contents')
        self.assertEqual(self.ledger.verify()['records'],4)
        with self.ledger.db() as db:records=[json.loads(row[0]) for row in db.execute('SELECT record FROM events ORDER BY seq')]
        self.assertEqual([r['event'] for r in records],['opened','closed','opened','closed'])
        self.assertEqual(records[-1]['receivedBytes'],len(b'private file contents'))
        self.assertTrue(all(r['subject']=='user:test' and r['source']=='198.51.100.6' and r['domain']=='allowed.example' for r in records))
        self.assertNotIn('secret-file',json.dumps(records));self.assertNotIn('private file contents',json.dumps(records))

if __name__=='__main__':unittest.main(verbosity=2)
