#!/usr/bin/env python3
"""Source notices and archives require the registered Browser lease."""
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'active-system'),str(ROOT/'active-system/codiserver-server-v0.3.0')]
from browser_service.http import BrowserHTTP
from browser_service.authorization import NetworkDenied

ID='A'*43
class Sessions:
    kind='registered'
    def principal(self,identifier,secret):
        if identifier!=ID or secret!='valid':raise NetworkDenied('bad lease')
        return SimpleNamespace(kind=self.kind,deadline=time.time()+60)

class SourceAccess(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory();root=Path(self.temp.name)
        (root/'index.html').write_text('<a href="release.tar.zst">source</a>')
        (root/'release.tar.zst').write_bytes(b'abcdefghij')
        (root/'private.txt').write_text('not in manifest')
        (root/'notice-manifest.json').write_text(json.dumps({'version':'codi-browser-notices/1','files':{'index.html':{}},'sourceArchives':{'release.tar.zst':'unused'}}))
        self.sessions=Sessions();app=web.Application()
        async def unused(_request):raise web.HTTPNotFound()
        BrowserHTTP(self.sessions,SimpleNamespace(handle=unused),origin='https://ksu.codes',source_root=root).routes(app)
        self.client=TestClient(TestServer(app));await self.client.start_server()
        self.path='/browser-relay/connection/'+ID+'/sources/'
    async def asyncTearDown(self):
        await self.client.close();self.temp.cleanup()
    async def get(self,path='',cookie=None,**headers):
        return await self.client.get(self.path+path,headers={'Host':'ksu.codes',**({'Cookie':'__Secure-codi-browser='+cookie} if cookie else {}),**headers})
    async def test_index_and_archive_require_registered_lease(self):
        for path in ('','release.tar.zst','notice-manifest.json'):
            r=await self.get(path);self.assertEqual(r.status,401)
        r=await self.get('',cookie='valid');self.assertEqual(r.status,200);self.assertIn('release.tar.zst',await r.text())
        r=await self.get('release.tar.zst',cookie='valid',Range='bytes=2-4');self.assertEqual(r.status,206);self.assertEqual(await r.read(),b'cde')
        r=await self.get('private.txt',cookie='valid');self.assertEqual(r.status,404)
        self.sessions.kind='anonymous';r=await self.get('',cookie='valid');self.assertEqual(r.status,401)
    async def test_duplicate_cookie_is_refused(self):
        r=await self.client.get(self.path,headers={'Host':'ksu.codes','Cookie':'__Secure-codi-browser=valid; __Secure-codi-browser=valid'})
        self.assertEqual(r.status,401)

if __name__=='__main__':unittest.main(verbosity=2)
