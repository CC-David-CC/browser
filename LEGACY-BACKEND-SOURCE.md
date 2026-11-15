# Retained legacy backend source

Owner: browser. Browser request/grant authority and desktop relay/source-launch helpers.

Legacy source only, not a current supported import path or command. Original cross-package namespaces, private imports, target paths, key/account custody, host/network/process actions and fixtures must be ported deliberately before use. Do not add sys.path shims, privileged globals, fake storage or automatic service/firewall actions to make it run. No old module/driver is imported or executed by this extraction; no active backend or minimum dependency changes.

## Source and history

Desktop snapshot `4f72ea86928666189b32f6f05c2c697a37341d06`; exact source baseline `92132846a65b699716795fedbe44f5ebe1e63c8d`; separate mechanical merge `7961e2291af00b7ae44872c133b2ae73d54dc880`. Private phase41 retains original/earlier paths, copy-boundary notes and commit/ref maps. No active package/module/test body changed.

| Original path | Retained path |
|---|---|
| `active-system/assets/desktop/browser-relay-client.mjs` | `legacy/backend/assets/desktop/browser-relay-client.mjs` |
| `active-system/assets/desktop/browser-source-launcher.mjs` | `legacy/backend/assets/desktop/browser-source-launcher.mjs` |
| `active-system/origin_service/browser_authority.py` | `legacy/backend/origin_service/browser_authority.py` |

These sources remain outside supported package/build/test entrypoints. Existing source baseline failures remain separate; syntax/history checks do not establish old protocol or current application compatibility. Preserve native signed-worker/authorization checks during a real public-interface port. External publication is not authorized by this source retention.

BrowserAuthority was copied from GuestAuthority at the original C082 boundary. Only Browser-specific path history is imported here. Earlier Guest lineage belongs to Linux and remains in original private recovery. The client header marker is a named HTTP authorization scheme concatenated with a caller-supplied token; no literal credential was approved.
