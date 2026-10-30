import asyncio
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from aiohttp import web
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from relay.download import Downloader,MAX_DOWNLOAD
from relay.policy import PolicyDenied,hostname

class FixturePolicy:
    def check_hostname(self,host,port):
        name=hostname(host)
        if name=='blocked.example':raise PolicyDenied('Blocked fixture host')
        return name
    def check_addresses(self,values):return tuple(values) # Test fixture only; permits loopback.

class DownloadTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.calls=[];self.blocked=False
        async def route(request):
            if request.path=='/redirect':raise web.HTTPFound('/file')
            if request.path=='/blocked':raise web.HTTPFound('http://blocked.example:'+str(self.port)+'/file')
            if request.path=='/large':return web.Response(body=b'x'*(MAX_DOWNLOAD+1))
            return web.Response(body=b'fixture\x00data',headers={'Content-Disposition':'attachment; filename="report.bin"'})
        app=web.Application();app.router.add_get('/{tail:.*}',route)
        self.runner=web.AppRunner(app);await self.runner.setup();site=web.TCPSite(self.runner,'127.0.0.1',0);await site.start();self.port=site._server.sockets[0].getsockname()[1]
        async def resolve(name,port):self.calls.append(name);return ['127.0.0.1']
        def check(ip):
            if self.blocked:raise PolicyDenied('IP blocked')
        self.relay=SimpleNamespace(policy_path='fixture',resolver=resolve,network_check=check)
        self.download=Downloader(self.relay,load_policy=lambda _:FixturePolicy())
        self.base='http://allowed.example:'+str(self.port)
    async def asyncTearDown(self):await self.runner.cleanup()

    async def test_download_and_redirect_are_checked(self):
        result=await self.download.fetch(self.base+'/redirect')
        self.assertEqual(result['data'],b'fixture\x00data');self.assertEqual(result['filename'],'report.bin')
        self.assertEqual(result['domains'],['allowed.example','allowed.example'])
        self.assertEqual(self.calls,['allowed.example','allowed.example'])
        with self.assertRaises(PolicyDenied):await self.download.fetch(self.base+'/blocked')
        self.assertNotIn('blocked.example',self.calls)

    async def test_size_and_literal_and_ip_blocks(self):
        with self.assertRaises(PolicyDenied):await self.download.fetch(self.base+'/large')
        with self.assertRaises(PolicyDenied):await self.download.fetch('http://127.0.0.1:'+str(self.port)+'/file')
        self.blocked=True
        with self.assertRaises(PolicyDenied):await self.download.fetch(self.base+'/file')
        with self.assertRaises(PolicyDenied):await self.download.fetch(self.base+'/file',check_alive=lambda:(_ for _ in ()).throw(PolicyDenied('expired')))

if __name__=='__main__':unittest.main()
