import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('browser_relay_policy', ROOT/'relay/policy.py')
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

class BrowserRelayPolicyTests(unittest.TestCase):
    def setUp(self):
        self.path = ROOT/'relay/policy.json'
        self.policy = module.DestinationPolicy.load(self.path)

    def test_named_sites_and_subdomains_blocked(self):
        for name in ['YouTube.com.', 'www.youtube-nocookie.com', 'a.googlevideo.com', 'dailymotion.com', 'brighteon.com', 'infowars.com', 'cnn.com', 'foxnews.com', 'facebook.com', 'x.com', 'bsky.app']:
            with self.subTest(name=name), self.assertRaises(module.PolicyDenied): self.policy.check_hostname(name, 443)
        self.assertEqual(self.policy.check_hostname('engineering.example.com', 443), 'engineering.example.com')
        self.assertEqual(self.policy.check_hostname('notyoutube.com', 443), 'notyoutube.com')

    def test_whitelist_is_prefilled_but_off(self):
        self.assertFalse(self.policy.whitelist_enabled)
        for name in ['grainger.com', 'www.mcmaster.com', 'digikey.com']:
            self.assertEqual(self.policy.check_hostname(name, 443), name)
        value = json.loads(self.path.read_text()); value['whitelistEnabled'] = True
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'policy.json'; path.write_text(json.dumps(value)); policy = module.DestinationPolicy.load(path)
            self.assertEqual(policy.check_hostname('www.grainger.com', 443), 'www.grainger.com')
            with self.assertRaises(module.PolicyDenied): policy.check_hostname('other.example.com', 443)
            with self.assertRaises(module.PolicyDenied): policy.check_hostname('www.youtube.com', 443)

    def test_resolution_is_pinned_and_private_or_mixed_answers_denied(self):
        self.assertEqual(self.policy.check_addresses(['1.1.1.1','1.1.1.1']), ('1.1.1.1',))
        for addresses in [['127.0.0.1'], ['10.1.2.3'], ['169.254.169.254'], ['::1'], ['::ffff:1.1.1.1'], ['1.1.1.1','192.168.1.1']]:
            with self.subTest(addresses=addresses), self.assertRaises(module.PolicyDenied): self.policy.check_addresses(addresses)

    def test_invalid_hosts_and_ports_fail_closed(self):
        for name in ['127.0.0.1', '[::1]', 'localhost', 'evil.example.com@youtube.com', 'foo..example.com', ' bad.example.com', '2130706433']:
            with self.subTest(name=name), self.assertRaises(module.PolicyDenied): self.policy.check_hostname(name, 443)
        with self.assertRaises(module.PolicyDenied): self.policy.check_hostname('grainger.com', 22)

    def test_duplicate_keys_fail(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'policy.json';path.write_text('{"version":"x","version":"y"}')
            with self.assertRaises(ValueError): module.DestinationPolicy.load(path)

if __name__ == '__main__': unittest.main()
