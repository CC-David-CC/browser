import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from relay.audit import AuditLedger
from relay.policy import DestinationPolicy

class OptionalRelayAuditTests(unittest.TestCase):
    def test_disabled_by_default(self):
        policy=DestinationPolicy.load(Path(__file__).resolve().parents[1]/'relay/policy.json')
        self.assertFalse(policy.server_audit_enabled)

    def test_signed_chain_and_aggregate_from_per_user_events(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger=AuditLedger(Path(directory)/'audit.sqlite3',Ed25519PrivateKey.generate())
            for sub,domain in [('user:a','grainger.com'),('user:b','grainger.com'),('user:a','mcmaster.com')]:
                event={'subject':sub,'source':'203.0.113.9','destination':domain,'port':443,'event':'opened'}
                ledger.append(event);ledger.append({**event,'event':'closed','sentBytes':10,'receivedBytes':20})
            checkpoint=ledger.verify();self.assertEqual(checkpoint['records'],6)
            aggregate={row['domain']:row for row in ledger.domains()}
            self.assertEqual(aggregate['grainger.com']['connections'],2)
            self.assertEqual(aggregate['grainger.com']['receivedBytes'],40)
            per_user={row['domain']:row for row in ledger.domains('user:a')}
            self.assertEqual(per_user['grainger.com']['connections'],1)
            self.assertEqual(per_user['mcmaster.com']['receivedBytes'],20)
            with ledger.db() as db:db.execute('DELETE FROM events WHERE seq=6')
            with self.assertRaises(ValueError):ledger.verify(checkpoint['head'])
            with ledger.db() as db:db.execute("UPDATE events SET record='{}' WHERE seq=1")
            with self.assertRaises(ValueError):ledger.verify()

    def test_rejects_payload_and_invalid_destinations_are_not_logged_raw(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger=AuditLedger(Path(directory)/'audit.sqlite3',Ed25519PrivateKey.generate())
            base={'subject':'user:a','source':'203.0.113.9','destination':'bad.example/secret','port':443,'event':'denied'}
            with self.assertRaises(ValueError):ledger.append({**base,'body':'private'})
            ledger.append(base)
            with ledger.db() as db:record=json.loads(db.execute('SELECT record FROM events').fetchone()[0])
            self.assertEqual(record['domain'],'(invalid)')
            self.assertNotIn('secret',json.dumps(record))

if __name__=='__main__':unittest.main()
