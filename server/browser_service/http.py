"""Same-origin admission routes for the browser Wisp relay.

This adapter requires trusted external ingress to enforce Host and provide the
real client address to the Relay. It does not start a listener by itself.
"""
import asyncio
import json
import re
from urllib.parse import urlsplit
from aiohttp import web
from .authorization import NetworkDenied

_ID=re.compile(r'[A-Za-z0-9_-]{43}\Z')

class BrowserHTTP:
    def __init__(self,sessions,relay,*,origin,base_path='',secure_cookie=True):
        u=urlsplit(origin)
        if not u.hostname or u.username or u.password or u.path or u.query or u.fragment or origin!=u.geturl() or (u.scheme!='https' and not (u.scheme=='http' and u.hostname=='127.0.0.1' and not secure_cookie)):
            raise ValueError('HTTPS origin or explicit loopback test origin required')
        self.sessions=sessions;self.relay=relay;self.origin=origin;self.host=u.netloc
        self.base=base_path+'/browser-relay';self.secure_cookie=secure_cookie
        self.cookie='__Secure-codi-browser' if secure_cookie else 'codi-browser-test'
        relay.authenticate=self.authenticate

    def routes(self,app):
        app.router.add_post(self.base+'/challenge',self.initial)
        root=self.base+'/connection/{connection}'
        app.router.add_post(root+'/challenge',self.challenge)
        app.router.add_post(root+'/authorize',self.authorize)
        app.router.add_post(root+'/close',self.close)
        app.router.add_get(root+'/wisp/',self.relay.handle)

    def headers(self,request):
        for name in ('Host','Origin'):
            if len(request.headers.getall(name,[]))!=1:raise web.HTTPForbidden()
        if request.host!=self.host or request.headers['Origin']!=self.origin:raise web.HTTPForbidden()
        if request.query_string or request.method!='POST' or request.content_type!='application/json' or request.headers.get('Content-Encoding') or request.headers.get('Transfer-Encoding'):
            raise web.HTTPBadRequest()
        if request.content_length is None or not 0<request.content_length<=16384:raise web.HTTPBadRequest()

    async def body(self,request,keys):
        self.headers(request)
        def unique(pairs):
            result={}
            for key,value in pairs:
                if key in result:raise ValueError('Duplicate key')
                result[key]=value
            return result
        try:
            async with asyncio.timeout(5):raw=await request.read()
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
        try:return self.response(self.sessions.create())
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

    async def authenticate(self,request):
        if request.query_string or len(request.headers.getall('Host',[]))!=1 or len(request.headers.getall('Origin',[]))!=1 or request.host!=self.host or request.headers['Origin']!=self.origin:raise web.HTTPForbidden()
        try:return self.sessions.principal(self.identifier(request),self.secret(request))
        except (NetworkDenied,ValueError):return None
