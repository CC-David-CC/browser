from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from relay.report_requests import ReportRequests
from test_report import report

class ReportRequestTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.now=1000
        self.coordinator=ReportRequests(Path(self.directory.name)/'reports.sqlite3',origin='https://ksu.codes',admin_subjects=['user:admin'],clock=lambda:self.now)
        self.admin=SimpleNamespace(kind='registered',sub='user:admin',deadline=99999)
        self.a=SimpleNamespace(kind='registered',sub='user:a',deadline=99999)
        self.b=SimpleNamespace(kind='registered',sub='user:b',deadline=99999)
    def tearDown(self):self.directory.cleanup()
    def test_explicit_request_and_per_account_aggregate(self):
        with self.assertRaises(PermissionError):self.coordinator.create(self.a)
        self.assertEqual(self.coordinator.pending(self.a),[])
        req=self.coordinator.create(self.admin,60);rid=req['id']
        a=report('user:a',('grainger.com','mcmaster.com'));b=report('user:b',('grainger.com',))
        with self.assertRaises(ValueError):self.coordinator.submit(self.b,rid,a)
        self.coordinator.submit(self.a,rid,a);self.coordinator.submit(self.a,rid,a);self.coordinator.submit(self.b,rid,b)
        total={x['domain']:x['requests'] for x in self.coordinator.summary(self.admin,rid)['domains']}
        self.assertEqual(total,{'grainger.com':2,'mcmaster.com':1})
        own=self.coordinator.summary(self.admin,rid,'user:a');self.assertEqual(sum(x['requests'] for x in own['domains']),2)
        with self.assertRaises(PermissionError):self.coordinator.summary(self.a,rid)
        self.now+=61
        with self.assertRaises(PermissionError):self.coordinator.submit(self.a,rid,a)
        self.coordinator.remove(self.admin,rid);self.assertEqual(self.coordinator.summary(self.admin,rid)['devices'],0)

if __name__=='__main__':unittest.main()
