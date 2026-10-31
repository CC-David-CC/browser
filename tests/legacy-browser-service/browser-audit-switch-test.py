#!/usr/bin/env python3
"""Test journaled audit toggles without changing any installed service."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'active-system'))
from browser_service import audit_switch

class AuditSwitchTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);root=Path(self.temp.name)
        self.policy=root/'policy.json';self.unit=root/'relay.service';self.journal=root/'journal.json'
        self.original=b'{"serverAuditEnabled": false, "blacklist": ["example.com"]}\n';self.policy.write_bytes(self.original);self.policy.chmod(0o600)
        self.unit.write_bytes(b'unit off\n');self.unit.chmod(0o644);self.restarts=0
    def restart(self):self.restarts+=1
    def validate(self,policy,unit):self.assertTrue(json.loads(policy)['serverAuditEnabled']);self.assertEqual(unit,b'unit on\n')
    def change(self,restart=None,check=lambda:None):return audit_switch.switch(self.policy,self.unit,self.journal,expected_unit=b'unit off\n',candidate_unit=b'unit on\n',enabled=True,validate=self.validate,restart=restart or self.restart,check=check)
    def test_success_changes_only_mode_and_unit(self):
        self.assertEqual(self.change()['status'],'enabled');self.assertEqual(json.loads(self.policy.read_bytes()),{'serverAuditEnabled':True,'blacklist':['example.com']});self.assertEqual(self.unit.read_bytes(),b'unit on\n');self.assertFalse(self.journal.exists());self.assertEqual(self.restarts,1)
    def test_restart_failure_restores_baseline(self):
        def restart():
            self.restarts+=1
            if self.restarts==1:raise RuntimeError('failed restart')
        with self.assertRaisesRegex(RuntimeError,'failed restart'):self.change(restart)
        self.assertEqual(self.policy.read_bytes(),self.original);self.assertEqual(self.unit.read_bytes(),b'unit off\n');self.assertFalse(self.journal.exists());self.assertEqual(self.restarts,2)
    def test_interruption_keeps_journal_and_recovers_without_overwriting_foreign_changes(self):
        def crash():raise SystemExit('simulated process loss')
        with self.assertRaises(SystemExit):self.change(crash)
        self.assertTrue(self.journal.exists());self.policy.write_text('{"other":true}')
        with self.assertRaisesRegex(ValueError,'changed outside'):audit_switch.recover(self.policy,self.unit,self.journal,restart=self.restart,check=lambda:None)
        self.assertTrue(self.journal.exists());self.policy.write_text(json.dumps({'serverAuditEnabled':True,'blacklist':['example.com']},indent=2)+'\n')
        self.assertEqual(audit_switch.recover(self.policy,self.unit,self.journal,restart=self.restart,check=lambda:None)['status'],'rolled-back')
        self.assertEqual(self.policy.read_bytes(),self.original);self.assertEqual(self.unit.read_bytes(),b'unit off\n');self.assertFalse(self.journal.exists())

if __name__=='__main__':unittest.main(verbosity=2)
