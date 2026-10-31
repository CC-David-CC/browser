"""Same-origin admission routes for the browser Wisp relay.

This adapter requires trusted external ingress to enforce Host and provide the
real client address to the Relay. It does not start a listener by itself.
"""
import asyncio
import json
import re
import time
from urllib.parse import quote
from urllib.parse import urlsplit
from aiohttp import ClientError, web
from cryptography.exceptions import InvalidSignature
from .authorization import NetworkDenied

_ID=re.compile(r'[A-Za-z0-9_-]{43}\Z')

async def disk_io(function,*args):
    task=asyncio.create_task(asyncio.to_thread(function,*args))
    try:return await asyncio.shield(task)
    except asyncio.CancelledError:
        try:await task
        finally:raise

class BrowserHTTP:
    def __init__(self,sessions,relay,*,origin,base_path='',secure_cookie=True,downloader=None,reports=None):
        u=urlsplit(origin)
        if not u.hostname or u.username or u.password or u.path or u.query or u.fragment or origin!=u.geturl() or (u.scheme!='https' and not (u.scheme=='http' and u.hostname=='127.0.0.1' and not secure_cookie)):
            raise ValueError('HTTPS origin or explicit loopback test origin required')
        self.sessions=sessions;self.relay=relay;self.origin=origin;self.host=u.netloc
        self.base=base_path+'/browser-relay';self.secure_cookie=secure_cookie
        self.cookie='__Secure-codi-browser' if secure_cookie else 'codi-browser-test'
        relay.authenticate=self.authenticate;self.downloader=downloader;self.downloads={};self.reports=reports
        self.report_slots=asyncio.Semaphore(2)

    def routes(self,app):
        app.router.add_post(self.base+'/challenge',self.initial)
        root=self.base+'/connection/{connection}'
        app.router.add_post(root+'/challenge',self.challenge)
        app.router.add_post(root+'/authorize',self.authorize)
        app.router.add_post(root+'/close',self.close)
        if self.downloader:app.router.add_post(root+'/download',self.download)
        if self.reports:
            app.router.add_post(root+'/reports/pending',self.report_pending)
            app.router.add_post(root+'/reports/role',self.report_role)
            app.router.add_post(root+'/reports/list',self.report_list)
            app.router.add_post(root+'/reports/submit',self.report_submit)
            app.router.add_post(root+'/reports/create',self.report_create)
            app.router.add_post(root+'/reports/summary',self.report_summary)
            app.router.add_post(root+'/reports/remove',self.report_remove)
        app.router.add_get(root+'/wisp/',self.relay.handle)

    def headers(self,request,maximum=16384):
        for name in ('Host','Origin'):
            if len(request.headers.getall(name,[]))!=1:raise web.HTTPForbidden()
        if request.host!=self.host or request.headers['Origin']!=self.origin:raise web.HTTPForbidden()
        if request.query_string or request.method!='POST' or request.content_type!='application/json' or request.headers.get('Content-Encoding') or request.headers.get('Transfer-Encoding'):
            raise web.HTTPBadRequest()
        if request.content_length is None or not 0<request.content_length<=maximum:raise web.HTTPBadRequest()

    async def body(self,request,keys,maximum=16384):
        self.headers(request,maximum)
        def unique(pairs):
            result={}
            for key,value in pairs:
                if key in result:raise ValueError('Duplicate key')
                result[key]=value
            return result
        try:
            async with asyncio.timeout(60 if maximum>16384 else 5):raw=await request.read()
            if len(raw)!=request.content_length:raise ValueError('Truncated body')
            value=json.loads(raw.decode('utf-8'),object_pairs_hook=unique)
            if not isinstance(value,dict) or set(value)!=set(keys):raise ValueError('Invalid request')
            return value
        except (ValueError,UnicodeError,TimeoutError):raise web.HTTPBadRequest() from None

    def identifier(self,request):
        value=request.match_info.get('connection','')
        if not _ID.fullmatch(value):raise web.HTTPNotFound()
        return value

    def secret(self,request):
        # Duplicate cookie names can create ambiguous authorization; reject.
        headers=request.headers.getall('Cookie',[])
        occurrences=sum(1 for header in headers for part in header.split(';') if part.strip().split('=',1)[0]==self.cookie)
        if occurrences!=1:raise NetworkDenied('Exactly one relay cookie required')
        return request.cookies.get(self.cookie)

    @staticmethod
    def response(value):return web.json_response(value,headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})

    async def initial(self,request):
        await self.body(request,[])
        try:
            challenge=self.sessions.create();challenge['report_requests']=bool(self.reports)
            return self.response(challenge)
        except NetworkDenied:raise web.HTTPTooManyRequests() from None

    async def challenge(self,request):
        await self.body(request,[]);identifier=self.identifier(request)
        try:return self.response(self.sessions.challenge(identifier,self.secret(request)))
        except (NetworkDenied,ValueError):raise web.HTTPUnauthorized() from None

    async def authorize(self,request):
        body=await self.body(request,['grant','proof']);identifier=self.identifier(request)
        try:
            # New connections do not yet have a cookie. Renewal must present it.
            secret=self.secret(request) if self.cookie in request.cookies else None
            lease,secret=self.sessions.authorize(identifier,body['grant'],body['proof'],secret=secret)
        except (NetworkDenied,ValueError,TypeError):raise web.HTTPUnauthorized() from None
        response=self.response({'expires_at':lease.deadline})
        response.set_cookie(self.cookie,secret,path=self.base+'/connection/'+identifier+'/',secure=self.secure_cookie,httponly=True,samesite='Strict')
        return response

    async def close(self,request):
        await self.body(request,[]);identifier=self.identifier(request)
        try:self.sessions.close(identifier,self.secret(request))
        except (NetworkDenied,ValueError):raise web.HTTPUnauthorized() from None
        response=self.response({'closed':True})
        response.del_cookie(self.cookie,path=self.base+'/connection/'+identifier+'/')
        return response

    async def report_call(self,request,keys,method,*,maximum=16384):
        self.headers(request,maximum);identifier=self.identifier(request)
        try:principal=self.sessions.principal(identifier,self.secret(request))
        except (NetworkDenied,ValueError):raise web.HTTPUnauthorized() from None
        if not principal:raise web.HTTPUnauthorized()
        try:
            async with self.report_slots:
                body=await self.body(request,keys,maximum)
                value=await disk_io(method,principal,*(body[key] for key in keys))
            return self.response(value)
        except PermissionError:raise web.HTTPForbidden() from None
        except (ValueError,TypeError,KeyError,InvalidSignature):raise web.HTTPBadRequest() from None

    async def report_pending(self,request):return await self.report_call(request,[],self.reports.pending)
    async def report_role(self,request):return await self.report_call(request,[],self.reports.role)
    async def report_list(self,request):return await self.report_call(request,[],self.reports.list_admin)
    async def report_create(self,request):return await self.report_call(request,['seconds'],self.reports.create)
    async def report_submit(self,request):return await self.report_call(request,['request','report'],self.reports.submit,maximum=12*1024*1024+4096)
    async def report_summary(self,request):return await self.report_call(request,['request','subject'],self.reports.summary)
    async def report_remove(self,request):return await self.report_call(request,['request'],self.reports.remove)

    async def download(self,request):
        body=await self.body(request,['url']);identifier=self.identifier(request)
        try:lease=self.sessions.principal(identifier,self.secret(request))
        except (NetworkDenied,ValueError):raise web.HTTPUnauthorized() from None
        if identifier in self.downloads or len(self.downloads)>=4 or list(self.downloads.values()).count(lease.sub)>=2:
            raise web.HTTPTooManyRequests(text='Download capacity reached; try again shortly')
        self.downloads[identifier]=lease.sub;result=None;response=None
        def alive():
            if lease.deadline<=time.time():raise NetworkDenied('Browser relay session expired')
        try:
            if getattr(self.relay,'audit_enabled',False):
                peer=self.relay.source(request)
                def audit_event(event,name,port,received):
                    self.relay.audit({'subject':lease.sub,'source':peer,'destination':name,'port':port,'event':event,'receivedBytes':received})
                result=await self.downloader.fetch(body['url'],check_alive=alive,audit_event=audit_event)
            else:
                result=await self.downloader.fetch(body['url'],check_alive=alive)
            name=str(result['filename'])[:512]
            response=web.StreamResponse(status=200,headers={'Content-Type':'application/octet-stream','Content-Length':str(result['bytes']),
                'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
                'X-Codi-Download-Name':quote(name,safe=''),
                'X-Codi-Domain-Requests':','.join(result['domains'])})
            await response.prepare(request)
            while True:
                alive()
                name,port,addresses=result['target']
                for address in addresses:self.relay.check_stream(name,port,address)
                chunk=await disk_io(result['file'].read,65536)
                if not chunk:break
                await response.write(chunk)
            await response.write_eof();return response
        except (ValueError,OSError,asyncio.TimeoutError,ClientError) as error:
            if response is not None and response.prepared:
                response.force_close()
                if request.transport:request.transport.close()
                return response
            # Only this explicit, bounded condition is safe to expose. Other
            # failures retain the generic message and cannot reveal internals.
            from relay.policy import DownloadTooLarge
            if isinstance(error,DownloadTooLarge):
                return web.json_response({'error':'Download is larger than 128 MiB.'},status=413,headers={'Cache-Control':'no-store'})
            return web.json_response({'error':'Download failed or was blocked by the network policy.'},status=403,headers={'Cache-Control':'no-store'})
        finally:
            if result is not None:result['file'].close()
            self.downloads.pop(identifier,None)

    async def authenticate(self,request):
        if request.query_string or len(request.headers.getall('Host',[]))!=1 or len(request.headers.getall('Origin',[]))!=1 or request.host!=self.host or request.headers['Origin']!=self.origin:raise web.HTTPForbidden()
        try:return self.sessions.principal(self.identifier(request),self.secret(request))
        except (NetworkDenied,ValueError):return None
