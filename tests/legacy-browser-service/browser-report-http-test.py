"""Real HTTP boundaries for optional, explicitly requested domain reports."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from aiohttp import web
from aiohttp.test_utils import TestClient,TestServer

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'server'),str(ROOT),str(ROOT/'tests')]
from browser_service.http import BrowserHTTP
from browser_service.authorization import NetworkDenied
from relay.report_requests import ReportRequests
from test_report import report

IDS={'a'*43:('secret-a','user:a'),'b'*43:('secret-b','user:b'),'c'*43:('secret-admin','user:admin')}
class Sessions:
    def principal(self,identifier,secret):
        expected=IDS.get(identifier)
        if not expected or expected[0]!=secret:raise NetworkDenied('Denied')
        return SimpleNamespace(kind='registered',sub=expected[1],deadline=99999)
class Relay:
    async def handle(self,request):raise web.HTTPNotImplemented()

class ReportsHTTP(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.reports=ReportRequests(Path(self.tmp.name)/'reports.sqlite3',origin='https://ksu.codes',admin_subjects=['user:admin'],clock=lambda:1000)
        app=web.Application(client_max_size=12*1024*1024+4096)
        BrowserHTTP(Sessions(),Relay(),origin='https://ksu.codes',reports=self.reports).routes(app)
        self.client=TestClient(TestServer(app));await self.client.start_server()
    async def asyncTearDown(self):await self.client.close()
    async def call(self,actor,action,body,*,origin='https://ksu.codes',secret=None):
        identifier={'a':'a'*43,'b':'b'*43,'admin':'c'*43}[actor]
        token=secret if secret is not None else IDS[identifier][0]
        return await self.client.post('/browser-relay/connection/'+identifier+'/reports/'+action,json=body,
            headers={'Host':'ksu.codes','Origin':origin,'Cookie':'__Secure-codi-browser='+token})
    async def test_explicit_requests_authentication_scope_and_aggregation(self):
        r=await self.call('a','pending',{});self.assertEqual(r.status,200);self.assertEqual(await r.json(),[])
        self.assertEqual((await self.call('a','create',{'seconds':60})).status,403)
        r=await self.call('a','role',{});self.assertEqual(await r.json(),{'admin':False})
        self.assertEqual((await self.call('a','list',{})).status,403)
        r=await self.call('admin','role',{});self.assertEqual(await r.json(),{'admin':True})
        self.assertEqual((await self.call('a','pending',{},secret='wrong')).status,401)
        self.assertEqual((await self.call('a','pending',{},origin='https://evil.invalid')).status,403)
        r=await self.call('admin','create',{'seconds':60});self.assertEqual(r.status,200);request=(await r.json())['id']
        r=await self.call('admin','list',{});self.assertEqual((await r.json())[0]['id'],request)
        self.assertEqual((await self.call('a','submit',{'report':report('user:b'),'request':request})).status,400)
        r=await self.call('a','submit',{'report':report('user:a'),'request':request});self.assertEqual(r.status,200)
        self.assertEqual((await self.call('b','summary',{'subject':None,'request':request})).status,403)
        r=await self.call('admin','summary',{'subject':'user:a','request':request});self.assertEqual(r.status,200)
        self.assertEqual(sum(x['requests'] for x in (await r.json())['domains']),2)
        self.assertEqual((await self.call('admin','remove',{'request':request})).status,200)
        self.assertEqual((await self.call('a','submit',{'request':request,'report':report('user:a')})).status,403)

if __name__=='__main__':unittest.main()
