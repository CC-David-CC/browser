# Managing live network rules

On box-webhost, `sudo codi-browser-policy` edits the root-owned policy files
with a lock, validates each result against the running relay's pinned policy
code, and replaces the file atomically. Changes apply to new connections;
outbound blocks also stop an active Browser stream when traffic next flows.
The relay rechecks current rules after DNS and while a Wisp connection is
being established. An already-issued TCP connection attempt cannot be undone;
a newly blocked connection is closed before Wisp payload is forwarded. For
explicit URL downloads, a rule change after the HTTP request has already been
sent cannot retract that request; the response is checked before processing
and while streaming.
The operator is pinned to the current relay's validation code. When upgrading
that relay, review and update the operator pin if its policy schema changes.

```sh
# Inspect independent incoming-login and outbound IP/country lists.
sudo codi-browser-policy access show

# Examples: a single incoming IP, an outgoing network, or a country.
sudo codi-browser-policy access add incomingLogin blockedCidrs 203.0.113.8
sudo codi-browser-policy access add outgoing blockedCidrs 198.51.100.0/24
sudo codi-browser-policy access add outgoing blockedCountries CA
sudo codi-browser-policy access remove outgoing blockedCountries CA

# Inspect and edit Browser domain lists.
sudo codi-browser-policy domains show
sudo codi-browser-policy domains add blacklist example.com
sudo codi-browser-policy domains remove blacklist example.com
sudo codi-browser-policy domains add whitelist supplier.example
sudo codi-browser-policy domains set whitelistEnabled on
sudo codi-browser-policy domains set whitelistEnabled off
```

The example IP ranges are documentation ranges; replace them with the intended
addresses. Use canonical CIDR ranges and uppercase two-letter country codes.
The domain whitelist is disabled by default; when enabled, the blacklist still
wins. Domain matching includes subdomains, but cannot block a service rehosted
under another name or reached through an allowed proxy. IP literals and
private/loopback destinations remain blocked by the Browser relay regardless
of domain list entries. Country data is approximate and can be unknown.

Incoming rules affect new logins and registrations; they do not revoke existing
sessions. Outgoing rules described here cover the Browser relay, not all server
egress or the separate Linux guest relay. The installed rule manager deliberately
does not enable the separate server audit ledger. See
`active-system/network_policy/README.md` for scope and tests.

## Optional server-side Browser metadata

The separate server ledger is **off by default**. Browser-local domain records
and administrator-requested device reports remain separate. On box-webhost:

```sh
sudo codi-browser-audit status
sudo codi-browser-audit enable
sudo codi-browser-audit report
sudo codi-browser-audit report --subject user:00000000-0000-4000-8000-000000000000
sudo codi-browser-audit disable
```

Enabling or disabling restarts the Browser relay and disconnects its open
streams. When enabled, the ledger records the registered account ID, trusted
visitor IP, destination domain and port, event time, and connection byte
counts for Browser relay traffic and explicit URL downloads. It does not record
page paths, messages, or file content, and does not cover the Linux guest or
other server egress. Country/IP and domain rules still apply.

The first enable creates a root-protected signing key at
`/etc/codi-browser/private/audit-signing-key` and a service-private ledger at
`/var/lib/codi-browser-audit/events.sqlite3`. Disable retains both for later
verification. Back up the key securely if those records matter: a lost key
cannot be silently replaced when a ledger exists. `report` verifies the chain
and shows aggregate totals by default; `--subject` limits it to an account.
Save a report's head hash separately and later pass it with `--expected-head`
to detect rollback or truncation relative to that saved point. A valid
signature does not prove the visitor's human identity or independently verify
the server's clock. Protect report output because it contains usage metadata.

If a transition is interrupted, `sudo codi-browser-audit status` reports a
pending journal; `sudo codi-browser-audit recover` restores its prior service
and policy after checking that neither was independently changed. Do not
remove the journal, key, or ledger as a routine recovery step.
