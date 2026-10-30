import base64
import hashlib
import json
from pathlib import Path
import sys
import unittest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec,utils
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from relay.report import verify_report,aggregate_reports

def report(subject='user:a',domains=('grainger.com','mcmaster.com')):
    private=ec.generate_private_key(ec.SECP256R1());public=private.public_key().public_numbers()
    encode=lambda n:base64.urlsafe_b64encode(n.to_bytes(32,'big')).decode().rstrip('=')
    key={'kty':'EC','crv':'P-256','x':encode(public.x),'y':encode(public.y)}
    scope=json.dumps(['https://ksu.codes',subject],separators=(',',':'));prev='0'*64;events=[]
    for seq,domain in enumerate(domains,1):
        at=1793390000000+seq;payload=json.dumps({'version':1,'scope':scope,'seq':seq,'prev':prev,'domain':domain,'at':at},separators=(',',':'));digest=hashlib.sha256(payload.encode()).hexdigest()
        sig=private.sign(bytes.fromhex(digest),ec.ECDSA(hashes.SHA256()));r,s=utils.decode_dss_signature(sig)
        events.append({'seq':seq,'prev':prev,'domain':domain,'at':at,'hash':digest,'signature':(r.to_bytes(32,'big')+s.to_bytes(32,'big')).hex()});prev=digest
    return {'version':1,'scope':scope,'publicKey':key,'events':events}

class DeviceReportTests(unittest.TestCase):
    def test_auth_scope_signatures_and_deduplication(self):
        data=report();valid=verify_report(data,subject='user:a',origin='https://ksu.codes');self.assertEqual(sum(x['requests'] for x in aggregate_reports([valid,valid])),2)
        with self.assertRaises(ValueError):verify_report(data,subject='user:b',origin='https://ksu.codes')
        data['events'][0]['domain']='changed.example'
        with self.assertRaises(ValueError):verify_report(data,subject='user:a',origin='https://ksu.codes')
    def test_checkpoint_detects_truncation(self):
        data=report();valid=verify_report(data,subject='user:a',origin='https://ksu.codes');data['events'].pop()
        with self.assertRaises(ValueError):verify_report(data,subject='user:a',origin='https://ksu.codes',expected_head=valid['head'])
if __name__=='__main__':unittest.main()
