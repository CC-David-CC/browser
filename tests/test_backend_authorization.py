"""Signed protocol qualification using Accounts' public JOSE primitives.

The fixture issuer is synthetic. This does not qualify an HTTP grant endpoint.
"""
import secrets
import unittest
from cryptography.hazmat.primitives.asymmetric import ec
from webos_accounts import jose
from browser_service.authorization import GRANT_TYPE, PROOF_TYPE, NetworkDenied
from browser_service.sessions import BrowserSessions


class BrowserAuthorization(unittest.TestCase):
    def setUp(self):
        self.now = 1000
        self.issuer = ec.generate_private_key(ec.SECP256R1())
        self.client = ec.generate_private_key(ec.SECP256R1())
        self.policy = {"mode": "server", "issuer": "https://webos.test",
                       "authorityKeys": [{"kid": "fixture", "jwk": jose.public_jwk(self.issuer)}]}
        self.sessions = BrowserSessions(self.policy, "a" * 64, clock=lambda: self.now)

    def signed(self, challenge, *, kind="registered", connection=None, signing_key=None):
        connection = connection or challenge["connection_id"]
        claims = {"v": 1, "iss": "https://webos.test", "aud": "https://webos.test/browser-relay",
                  "sub": "user:12345678-1234-1234-1234-123456789abc", "sid": "fixture-session",
                  "kind": kind, "cnf": {"jwk": jose.public_jwk(self.client)}, "iat": self.now,
                  "exp": self.now + 20, "jti": secrets.token_urlsafe(32), "nonce": challenge["nonce"],
                  "connection_id": connection, "policy_sha256": "a" * 64, "session_deadline": self.now + 60}
        grant = jose.sign(claims, signing_key or self.issuer, GRANT_TYPE, "fixture")
        proof = jose.sign({"v": 1, "iss": "fixture-session", "aud": claims["aud"],
                           "nonce": claims["nonce"], "grant_sha256": jose.digest(grant),
                           "connection_id": connection, "policy_sha256": "a" * 64,
                           "method": "CONNECT", "path": "/browser-relay", "iat": self.now,
                           "exp": self.now + 20}, self.client, PROOF_TYPE)
        return grant, proof

    def test_registered_lease_uses_live_principal_and_secret(self):
        challenge = self.sessions.create()
        lease, secret = self.sessions.authorize(challenge["connection_id"], *self.signed(challenge))
        self.assertIs(self.sessions.principal(challenge["connection_id"], secret), lease)
        self.assertEqual(lease.sub, "user:12345678-1234-1234-1234-123456789abc")
        with self.assertRaises(NetworkDenied):
            self.sessions.principal(challenge["connection_id"], "wrong")

    def test_untrusted_signature_cannot_create_lease(self):
        challenge = self.sessions.create()
        other = ec.generate_private_key(ec.SECP256R1())
        with self.assertRaises(jose.Invalid):
            self.sessions.authorize(challenge["connection_id"], *self.signed(challenge, signing_key=other))

    def test_grant_for_another_connection_is_denied(self):
        challenge = self.sessions.create()
        other = self.sessions.create()
        with self.assertRaises(NetworkDenied):
            self.sessions.authorize(other["connection_id"], *self.signed(challenge))

    def test_anonymous_identity_cannot_create_lease(self):
        challenge = self.sessions.create()
        with self.assertRaises(NetworkDenied):
            self.sessions.authorize(challenge["connection_id"], *self.signed(challenge, kind="default"))

    def test_consumed_challenge_cannot_authorize_twice(self):
        challenge = self.sessions.create()
        signed = self.signed(challenge)
        _, secret = self.sessions.authorize(challenge["connection_id"], *signed)
        with self.assertRaises(NetworkDenied):
            self.sessions.authorize(challenge["connection_id"], *signed, secret=secret)

    def test_expiry_and_close_invalidate_principal(self):
        challenge = self.sessions.create()
        lease, secret = self.sessions.authorize(challenge["connection_id"], *self.signed(challenge))
        self.now += 21
        with self.assertRaises(NetworkDenied):
            self.sessions.principal(challenge["connection_id"], secret)
        second = self.sessions.create()
        _, secret = self.sessions.authorize(second["connection_id"], *self.signed(second))
        self.sessions.close(second["connection_id"], secret)
        with self.assertRaises(NetworkDenied):
            self.sessions.principal(second["connection_id"], secret)


if __name__ == "__main__":
    unittest.main(verbosity=2)
