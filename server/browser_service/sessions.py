"""Short-lived, in-memory browser-relay admission and lease renewal.

The HTTP adapter must enforce exact same-origin requests and keep the returned
secret in a Secure, HttpOnly, SameSite=Strict cookie scoped to this connection.
Identifiers are not credentials; they may appear in paths. Never put a cookie
secret, grant, or signing proof in a URL. A process restart invalidates all
admissions. This module does not itself create an HTTP listener.
"""
import secrets
import threading
import time
from dataclasses import dataclass
from .authorization import NetworkDenied, WireAuthorization

@dataclass
class BrowserLease:
    sub: str
    sid: str
    kind: str
    key: dict
    deadline: int

class BrowserSessions:
    def __init__(self, issuer_policy, policy_sha256, *, base_path='', clock=time.time, capacity=512):
        if type(capacity) is not int or not 1 <= capacity <= 4096:
            raise ValueError('Bounded relay admission capacity required')
        self.issuer_policy=issuer_policy;self.policy_sha256=policy_sha256
        self.base_path=base_path;self.clock=clock;self.capacity=capacity
        self.lock=threading.RLock();self.records={}

    def _clean(self):
        now=int(self.clock())
        for key,record in list(self.records.items()):
            expiry=record['lease'].deadline if record['lease'] else record['pending_deadline']
            if expiry<=now:
                record['wire'].close();del self.records[key]

    def create(self):
        with self.lock:
            self._clean()
            if len(self.records)>=self.capacity:raise NetworkDenied('Browser relay admission capacity reached')
            wire=WireAuthorization(self.issuer_policy,self.policy_sha256,base_path=self.base_path,clock=self.clock)
            challenge=wire.challenge();identifier=wire.connection_id
            self.records[identifier]={'wire':wire,'pending_deadline':challenge['expires_at'],'lease':None,'secret':None}
            return challenge

    def _record(self,identifier):
        if not isinstance(identifier,str):raise NetworkDenied('Invalid connection')
        self._clean();record=self.records.get(identifier)
        if record is None:raise NetworkDenied('Browser relay session expired')
        return record

    def _verify_secret(self,record,secret):
        if not isinstance(secret,str) or not record['secret'] or not secrets.compare_digest(record['secret'],secret):
            raise NetworkDenied('Browser relay credential required')

    def authorize(self,identifier,grant,proof,*,secret=None):
        with self.lock:
            record=self._record(identifier);old=record['lease']
            if old:self._verify_secret(record,secret)
            principal=record['wire'].accept(grant,proof)
            if old:
                if (principal.subject,principal.sid,principal.kind,principal.key)!=(old.sub,old.sid,old.kind,old.key):
                    old.deadline=0;record['wire'].close();del self.records[identifier]
                    raise NetworkDenied('Browser relay identity changed')
                old.deadline=principal.deadline
            else:
                old=BrowserLease(principal.subject,principal.sid,principal.kind,principal.key,principal.deadline)
                record['lease']=old;record['secret']=secrets.token_urlsafe(32)
            return old,record['secret']

    def challenge(self,identifier,secret):
        with self.lock:
            record=self._record(identifier);self._verify_secret(record,secret)
            return record['wire'].challenge()

    def principal(self,identifier,secret):
        with self.lock:
            record=self._record(identifier);self._verify_secret(record,secret)
            return record['lease']

    def close(self,identifier,secret):
        with self.lock:
            record=self._record(identifier);self._verify_secret(record,secret)
            record['wire'].close();record['lease'].deadline=0;del self.records[identifier]
