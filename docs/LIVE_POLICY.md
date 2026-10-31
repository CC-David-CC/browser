# Managing live network rules

On box-webhost, `sudo codi-browser-policy` edits the root-owned policy files
with a lock, validates each result against the running relay's pinned policy
code, and replaces the file atomically. Changes apply to new connections;
outbound blocks also stop an active Browser stream when traffic next flows.
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
