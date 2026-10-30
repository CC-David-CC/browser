"""Operator-owned destination policy for a future authenticated browser relay.

This module does not start a relay. Callers must check EVERY connection request,
resolve on the relay, then connect to an exact vetted address; never resolve a
second time when connecting. Domain lists cannot identify all content hosted on
other domains, tunneled traffic, or services accessed through unrelated proxies.
"""
from dataclasses import dataclass
import ipaddress
import json
from pathlib import Path
import re

class PolicyDenied(ValueError):
    pass

def hostname(value):
    if not isinstance(value, str) or not value or len(value) > 254 or value != value.strip():
        raise PolicyDenied('Invalid destination hostname')
    try:
        name = value.rstrip('.').encode('idna').decode('ascii').lower()
    except UnicodeError as error:
        raise PolicyDenied('Invalid destination hostname') from error
    if len(name) > 253 or not name or not re.fullmatch(r'[a-z0-9.-]+', name):
        raise PolicyDenied('Invalid destination hostname')
    labels = name.split('.')
    if len(labels) < 2 or any(not 1 <= len(label) <= 63 or label.startswith('-') or label.endswith('-') for label in labels):
        raise PolicyDenied('Invalid destination hostname')
    try:
        ipaddress.ip_address(name)
    except ValueError:
        pass
    else:
        raise PolicyDenied('IP-literal destinations are disabled')
    if all(label.isdigit() for label in labels):
        raise PolicyDenied('IP-like destination is disabled')
    return name

def matches(name, entries):
    return any(name == domain or name.endswith('.' + domain) for domain in entries)

@dataclass(frozen=True)
class DestinationPolicy:
    blacklist: tuple
    whitelist: tuple
    whitelist_enabled: bool
    tcp_ports: tuple
    max_connections_per_user: int

    @classmethod
    def load(cls, path):
        raw = Path(path).read_bytes()
        if len(raw) > 65536: raise ValueError('Policy too large')
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result: raise ValueError('Duplicate policy key')
                result[key] = value
            return result
        data = json.loads(raw, object_pairs_hook=unique)
        if not isinstance(data, dict) or set(data) != {'version', 'blacklist', 'whitelist', 'whitelistEnabled', 'tcpPorts', 'maxConnectionsPerUser'} or data['version'] != 'codi-browser-relay-policy/1':
            raise ValueError('Invalid relay policy')
        def domains(values):
            if not isinstance(values, list) or len(values) > 4096: raise ValueError('Invalid domain list')
            out = tuple(hostname(value) for value in values)
            if len(out) != len(set(out)): raise ValueError('Duplicate policy domain')
            return out
        if type(data['whitelistEnabled']) is not bool: raise ValueError('Invalid whitelist switch')
        ports = data['tcpPorts']
        if not isinstance(ports, list) or not ports or len(ports) > 16 or any(type(p) is not int or not 1 <= p <= 65535 for p in ports) or len(set(ports)) != len(ports): raise ValueError('Invalid port policy')
        limit = data['maxConnectionsPerUser']
        if type(limit) is not int or not 1 <= limit <= 128: raise ValueError('Invalid connection limit')
        return cls(domains(data['blacklist']), domains(data['whitelist']), data['whitelistEnabled'], tuple(ports), limit)

    def check_hostname(self, raw, port):
        name = hostname(raw)
        if type(port) is not int or port not in self.tcp_ports: raise PolicyDenied('Destination port is not allowed')
        if matches(name, self.blacklist): raise PolicyDenied('Destination is blocked')
        if self.whitelist_enabled and not matches(name, self.whitelist): raise PolicyDenied('Destination is not on the whitelist')
        return name

    def check_addresses(self, addresses):
        if not addresses: raise PolicyDenied('No destination addresses')
        result = []
        for raw in addresses:
            try: address = ipaddress.ip_address(raw)
            except ValueError as error: raise PolicyDenied('Invalid resolved address') from error
            # Reject the whole answer if it mixes public and private addresses;
            # the caller connects only to one of these exact validated addresses.
            if not address.is_global or address.is_multicast or address.is_unspecified or (isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None):
                raise PolicyDenied('Non-public resolved address')
            result.append(str(address))
        return tuple(dict.fromkeys(result))
