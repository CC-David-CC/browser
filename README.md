# Browser (experimental)

This app is intended to run an independent Gecko/SpiderMonkey engine in the
visitor's browser, painting into its own desktop window. Pages do not receive
CodiServer app services. Each window owns its engine worker and temporary
profile; closing or resetting it discards that profile.

**Status:** the Browser app, pinned Gecko engine, and authenticated,
policy-controlled Wisp relay are live at ksu.codes. Registered-account tests
cover basic navigation, destination policy, HTML opening, clicked downloads,
and independent windows. Desktop and phone-sized tests do not establish
broad website compatibility or replace a security audit. It is not ready for
sensitive browsing or untrusted users.

The regular app builder packages the entry and worker support declared in
`app.json`. A usable build also needs the actual engine assets and corresponding
manifest packaged and tested; the generated engine assets are not stored in Git.
Build inputs and exact revisions are in `upstream.lock.json`, `native/` and
`tools/`. Development-only tests, harness and fixtures are in `tests/`, `demo/`
and `fixtures/`.

Read `docs/AGENT_HANDOFF.md` and `docs/SECURITY.md` before integrating or enabling
networking. The upstream engine differs from a fully sandboxed native Firefox.
The original adapter is MIT licensed; see `docs/LICENSE` and
`docs/THIRD_PARTY_NOTICES.md` for distribution requirements. The supplied
`docs/SOURCE_MANIFEST.json` describes the original handoff, before this folder
was reorganized; it is not a manifest of the current files.
`docs/SOURCE_PROVISION.md` records the exact source snapshots and local patch
for the current engine build, along with the outstanding distribution review.

## Build or update the engine

The source is pinned: `upstream.lock.json` records the outer Firefox-WASM
commit, its Gecko fork commit, the Emscripten version and the adapter ABI. The
current build targets Linux and requires Git, Python 3, Node.js, GNU make,
pnpm **9.12.0** (the upstream lockfile version), Rust **1.95** with `rust-src`
and the `wasm32-unknown-emscripten` target, zstd,
CMake, Ninja, pkg-config, a host C/C++ compiler, and the PulseAudio development
headers. The build downloads a patched Emscripten 6.0.1 toolchain and additional
Mozilla build dependencies. It needs substantial disk, memory and build time;
use a separate build directory on a disk with plenty of free space. Run as an
ordinary user, not root. Node and these tools are for building; visitors do not
need to install them.

From this directory, with the prerequisites available on `PATH`:

```sh
bash tools/check.sh
python3 tools/fetch_engine.py --into /path/to/build/firefox-wasm
python3 tools/patch_engine.py /path/to/build/firefox-wasm
git -C /path/to/build/firefox-wasm status --short
git -C /path/to/build/firefox-wasm diff  # Also review gecko.js/src/embed-host.cpp.
bash tools/build_engine.sh /path/to/build/firefox-wasm
python3 tools/serve.py --port 8087
```

The build script checks both pinned commits and patch hashes, builds the raw
engine, and stages `engine/gecko.js`, `engine/gecko.wasm`, `engine/gecko.data`,
`engine/wisp-client.mjs` and `engine/manifest.json`. These are generated files
and are excluded from Git. The manifest hashes identify the staged artifacts;
they do not establish that the sources are trustworthy or the browser is safe.
The isolated server is at `http://127.0.0.1:8087/demo/`; its test-only CSP
allows the runtime's blob scripts and is not the live desktop policy.

To update upstream, deliberately review the new outer and inner revisions,
the Gecko licenses, Emscripten/Rust requirements, native mailbox ABI, and
`tools/patch_engine.py` anchors. Update the pins in `upstream.lock.json` and
`src/policy.mjs` together, use a fresh checkout, review the regenerated patch,
run the offline tests, and rebuild. Do not substitute upstream's `dist/gecko.js`
UI bundle for the raw runtime. A staged build alone does not mean it works:
run the real-engine tests in `docs/ACCEPTANCE.md`, including multiple windows,
close/reset during initialization, worker cleanup and input, before releasing it on the desktop. The app asset manifest and the builder and
catalog limits have been updated for this engine; verify CSP and cross-origin isolation on the
target desktop. The current live desktop blocks the adapter's blob script
loading. Do not weaken the whole site's policy without an appropriate review.

Online browsing is a separate step: configure only an authenticated Wisp relay
with server-enforced destination and resource policies, and test TLS and access
controls. The current `wispURL` is `null`; the v86 relay is not automatically a
Wisp relay. Never commit runtime binaries, downloaded toolchains, profiles,
credentials or user data.

The 2026-10-30 development build produced about 227 MiB of WebAssembly and
13 MiB of engine data, before compression. These sizes and runtime memory use
matter on phones and limited connections; loading must remain on demand.

## Relay destination policy

`relay/policy.json` is the operator-editable template for the server relay. The blacklist includes the requested video, news and social
services and their listed subdomains. The whitelist is prefilled with Grainger,
McMaster-Carr and other engineering suppliers, but `whitelistEnabled` is
`false`. When enabled, a destination must match the whitelist and not match the
blacklist. Search engines are not intentionally listed. TCP ports 80 and 443
are the initial permitted ports.

`relay/policy.py` validates that configuration and checks names and resolved
addresses. The live relay checks destinations on each connection and connects
to a vetted address, including for redirects and page subrequests. IP literals and private/loopback
addresses are denied. Domain lists require maintenance and cannot guarantee
blocking content rehosted on unrelated domains or accessed through other
proxies. The separate root-owned live policy is enforced by the Browser relay;
this source file is its starting template, not the active operator copy.

The desktop implementation can open selected `.html`/`.htm` files from My
files as well as upload a local HTML file. It copies the selected document to
the temporary guest profile; sibling files and persistent browser profiles are
not implemented yet. The live relay also supports an explicit Download
URL action into My files, limited to 128 MiB. That independent fetch does not
include Gecko cookies. Downloads clicked inside
Gecko use its own session and appear in a temporary queue; choose Save to My
files to keep one. See `docs/CLICKED_DOWNLOADS.md` for limits and testing.
Every redirect is checked against the relay destination policy.

## Domain usage records

The Browser app records requested destination domains locally by
account when its relay is connected. Records contain a domain and device time,
not page URLs, paths, messages or content. The device uses a non-exportable
Web Crypto signing key and a hash chain; multiple tabs serialize updates with
Web Locks. A separately saved head hash detects missing or changed records.
Clearing the browser's site data removes the records and key. The private key
never leaves the browser. The live coordinator verifies reports against an authenticated
account and combines device reports without double-counting repeated snapshots.
An administrator can request reports from Browser's Diagnostics section; see
`docs/DOMAIN_REPORTS.md` for the live test and operating details. A signature shows
that a particular key signed a report; it does not prove a person visited a
site, that the device clock was accurate, or that a user-controlled client
reported every request.

The operator's independent server ledger is controlled by
`serverAuditEnabled` in `relay/policy.json` and is **false by default**. The
ledger code can sign a hash chain of authenticated connection metadata and
produce per-account or all-account domain summaries from the same events. It
is live but disabled; an operator can explicitly enable it as described in
`docs/LIVE_POLICY.md`. Save checkpoints outside the database to detect deletion
or rewriting of the tail. The signed times
are the server's clock, not independently certified timestamps. No page
content or message body belongs in these records.

The relay uses `aiohttp` and `cryptography` in an isolated environment. A live
test registered a disposable account, obtained a signed relay grant, fetched
an allowed HTTPS page, rejected a blacklisted domain and private addresses,
opened a Wisp connection, then removed the test account. Broader site
compatibility and real phone use remain to be verified.

The relay implements bounded Wisp v1 TCP streams,
checks the destination policy before resolving and connects only to a vetted
public address. Its test fixture exercised a real Gecko request through the
relay, rejected a YouTube request before DNS lookup, and stored signed domain
requests in the test browser. That earlier fixture supplied a fake test identity and local destination. A
later isolated desktop test used the real local issuer and rendered a public
HTTPS page through the authenticated relay. The backend endpoint is now public
and requires a registered, signed session for networking. These checks are not a broad website compatibility or security
audit. Optional server audit remains disabled unless the operator enables it.

IP-range and country controls are independent of the domain lists. Their
source template and rollout notes are in `active-system/network_policy/README.md`.
They cover live login and Browser relay traffic; other egress paths are not
yet covered by these shared rules.

The live request coordinator stores received reports only after an explicit
administrator request; it uses a private database and configured administrator
account ID. The operator can remove stored request results. Device-reported usage is not a
complete or independently verified account of what a person did.

## Phone input (development)

On a touch screen, a tap is sent to Gecko as a click and a drag scrolls the
page instead of clicking it. The Browser toolbar's Keyboard button explicitly
shows the device keyboard for the page field that was last tapped. A local
Chrome phone-emulation test exercised a real Gecko field and touch scrolling;
it does not verify the physical Android keyboard, all input methods, selection,
drag-and-drop, or accessibility. Desktop pointer behavior remains available.
The keyboard bridge sends committed text to Gecko; complex composition and
suggestion replacements still need device testing.
