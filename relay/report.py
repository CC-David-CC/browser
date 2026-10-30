"""Verify and aggregate device reports after account authentication.

This module provides no endpoint or identity verification. The caller must
supply the already-authenticated subject and expected origin. Browser-held
keys and timestamps do not prove a human's identity or complete reporting.
"""
import base64
import hashlib
import json
import re
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils


def _coordinate(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',value):raise ValueError('Invalid public key coordinate')
    raw=base64.urlsafe_b64decode(value+'=')
    if len(raw)!=32 or base64.urlsafe_b64encode(raw).decode().rstrip('=')!=value:raise ValueError('Noncanonical key coordinate')
    return int.from_bytes(raw,'big')


def verify_report(report,*,subject,origin,expected_head=None):
    if not isinstance(subject,str) or not subject.startswith('user:') or len(subject)>100 or not isinstance(origin,str):raise ValueError('Authenticated account and origin required')
    if not isinstance(report,dict) or set(report)!={'version','scope','publicKey','events'} or report['version']!=1 or not isinstance(report['scope'],str) or json.loads(report['scope'])!=[origin,subject]:raise ValueError('Wrong report scope')
    jwk=report['publicKey']
    if not isinstance(jwk,dict) or jwk.get('kty')!='EC' or jwk.get('crv')!='P-256' or 'd' in jwk:raise ValueError('Invalid public key')
    public=ec.EllipticCurvePublicNumbers(_coordinate(jwk.get('x')),_coordinate(jwk.get('y')),ec.SECP256R1()).public_key()
    identity=json.dumps({'crv':'P-256','kty':'EC','x':jwk['x'],'y':jwk['y']},sort_keys=True,separators=(',',':'))
    key_id=hashlib.sha256(identity.encode()).hexdigest()
    events=report['events']
    if not isinstance(events,list) or len(events)>100000:raise ValueError('Invalid report size')
    prev='0'*64;result=[]
    for seq,event in enumerate(events,1):
        if not isinstance(event,dict) or set(event)!={'seq','prev','domain','at','hash','signature'} or type(event['seq']) is not int or event['seq']!=seq or event['prev']!=prev:raise ValueError('Invalid event chain')
        domain=event['domain'];at=event['at'];digest=event['hash'];signature=event['signature']
        if not isinstance(domain,str) or len(domain)>253 or not re.fullmatch(r'[a-z0-9.:-]+',domain) or type(at) is not int or not 0<=at<2**53 or not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest) or not isinstance(signature,str) or not re.fullmatch('[0-9a-f]{128}',signature):raise ValueError('Invalid event metadata')
        payload=json.dumps({'version':1,'scope':report['scope'],'seq':seq,'prev':prev,'domain':domain,'at':at},ensure_ascii=False,separators=(',',':'))
        if hashlib.sha256(payload.encode()).hexdigest()!=digest:raise ValueError('Event hash changed')
        raw=bytes.fromhex(signature);sig=utils.encode_dss_signature(int.from_bytes(raw[:32],'big'),int.from_bytes(raw[32:],'big'))
        public.verify(sig,bytes.fromhex(digest),ec.ECDSA(hashes.SHA256()))
        prev=digest;result.append({'seq':seq,'domain':domain,'at':at,'hash':digest})
    if expected_head is not None and prev!=expected_head:raise ValueError('Report differs from saved checkpoint')
    return {'subject':subject,'deviceKey':key_id,'head':prev,'events':result}


def aggregate_reports(reports):
    """Merge snapshots once per subject/device/sequence, rejecting forks."""
    seen={};totals={}
    for report in reports:
        for event in report['events']:
            key=(report['subject'],report['deviceKey'],event['seq'])
            if key in seen:
                if seen[key]!=event['hash']:raise ValueError('Conflicting device history')
                continue
            seen[key]=event['hash'];domain=event['domain'];totals[domain]=totals.get(domain,0)+1
    return [{'domain':domain,'requests':count} for domain,count in sorted(totals.items(),key=lambda x:(-x[1],x[0]))]
