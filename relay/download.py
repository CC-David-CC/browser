"""Bounded server-mediated URL download into the visitor's account files.

This fetches an explicitly supplied URL, not the Gecko profile: cookies and
other browser credentials are deliberately not copied. Every redirect gets a
fresh policy and DNS check, and the connector receives only validated addresses.
"""
import asyncio
import ipaddress
import socket
import tempfile
from pathlib import PurePosixPath
from aiohttp import ClientSession, ClientTimeout, TCPConnector, hdrs
from aiohttp.abc import AbstractResolver
from yarl import URL
from .policy import DestinationPolicy, PolicyDenied, DownloadTooLarge

MAX_DOWNLOAD=128*1024*1024
MAX_REDIRECTS=5
MAX_TRANSFER_SECONDS=30*60
READ_IDLE_SECONDS=60

async def disk_io(function,*args):
    task=asyncio.create_task(asyncio.to_thread(function,*args))
    try:return await asyncio.shield(task)
    except asyncio.CancelledError:
        try:await task
        finally:raise

class CheckedResolver(AbstractResolver):
    def __init__(self,policy,resolver,check):self.policy=policy;self.resolver=resolver;self.check=check;self.allowed=[]
    async def resolve(self,host,port=0,family=socket.AF_UNSPEC):
        values=self.policy.check_addresses(await self.resolver(host,port))
        self.allowed=list(values)
        for ip in values:self.check(ip)
        return [{'hostname':host,'host':ip,'port':port,'family':socket.AF_INET6 if ipaddress.ip_address(ip).version==6 else socket.AF_INET,'proto':0,'flags':socket.AI_NUMERICHOST} for ip in values]
    async def close(self):pass

class Downloader:
    def __init__(self,relay,*,load_policy=DestinationPolicy.load):self.relay=relay;self.load_policy=load_policy
    async def fetch(self,value,*,check_alive=lambda:None,audit_event=lambda *_args:None):
        if not isinstance(value,str) or len(value)>8192:raise PolicyDenied('Invalid download URL')
        try:url=URL(value)
        except ValueError:raise PolicyDenied('Invalid download URL') from None
        domains=[]
        for step in range(MAX_REDIRECTS+1):
            check_alive()
            if url.scheme not in ('http','https') or not url.host or url.user is not None or url.password is not None or url.fragment:
                raise PolicyDenied('Use an HTTP or HTTPS URL without credentials or a fragment')
            policy=self.load_policy(self.relay.policy_path);port=url.port
            if hasattr(self.relay,'audit_enabled') and policy.server_audit_enabled!=self.relay.audit_enabled:
                raise PolicyDenied('Audit mode changed; restart relay')
            try:name=policy.check_hostname(url.host,port)
            except PolicyDenied:
                audit_event('denied',url.host,port,0)
                raise
            domains.append(name)
            resolver=CheckedResolver(policy,self.relay.resolver,self.relay.network_check)
            connector=TCPConnector(resolver=resolver,use_dns_cache=False,force_close=True,limit=1)
            timeout=ClientTimeout(total=MAX_TRANSFER_SECONDS,connect=10,sock_read=READ_IDLE_SECONDS)
            opened=False;size=0;content=None
            try:
              async with ClientSession(connector=connector,timeout=timeout,trust_env=False,auto_decompress=False) as session:
                async with session.get(url,allow_redirects=False,headers={hdrs.ACCEPT_ENCODING:'identity'}) as response:
                    audit_event('opened',name,port,0);opened=True
                    if response.status in (301,302,303,307,308):
                        if step==MAX_REDIRECTS:raise PolicyDenied('Too many download redirects')
                        target=response.headers.get('Location')
                        if not target or len(target)>8192:raise PolicyDenied('Invalid download redirect')
                        try:url=url.join(URL(target))
                        except ValueError:raise PolicyDenied('Invalid download redirect') from None
                        continue
                    if response.status!=200:raise PolicyDenied('Download server returned HTTP '+str(response.status))
                    if response.headers.get('Content-Encoding','identity').lower() not in ('','identity'):
                        raise PolicyDenied('Compressed download response is not supported')
                    if response.content_length is not None and response.content_length>MAX_DOWNLOAD:raise DownloadTooLarge('Download is larger than 128 MiB')
                    # Keep large downloads on private temporary disk rather than
                    # accumulating a copy in the relay's memory. The caller owns
                    # and must close the unlinked temporary file.
                    content=tempfile.TemporaryFile(mode='w+b')
                    try:
                        async for chunk in response.content.iter_chunked(65536):
                            check_alive()
                            for ip in resolver.allowed:
                                if hasattr(self.relay,'check_stream'):self.relay.check_stream(name,port,ip)
                                else:self.relay.network_check(ip)
                            size+=len(chunk)
                            if size>MAX_DOWNLOAD:raise DownloadTooLarge('Download is larger than 128 MiB')
                            await disk_io(content.write,chunk)
                        await disk_io(content.seek,0)
                        filename=response.content_disposition.filename if response.content_disposition else None
                        if not filename:filename=PurePosixPath(url.path).name or 'download'
                        return {'file':content,'bytes':size,'filename':filename,'domains':domains,'target':(name,port,tuple(resolver.allowed))}
                    except BaseException:
                        content.close();raise
            finally:
                try:audit_event('closed' if opened else 'denied',name,port,size)
                except BaseException:
                    if content is not None:content.close()
                    raise
        raise PolicyDenied('Too many redirects')
