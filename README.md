# Browser (experimental)

This app is intended to run an independent Gecko/SpiderMonkey engine in the
visitor's browser, painting into its own desktop window. Pages do not receive
CodiServer app services. Each window owns its engine worker and temporary
profile; closing or resetting it discards that profile.

**Status:** adapter source only. The pinned Gecko engine has not yet been built
or tested, and this app is not registered in the desktop menu. Public website
access also needs an authenticated, policy-controlled Wisp relay; none is
configured. It is not ready for sensitive browsing or untrusted users.

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

## Build or update the engine

The source is pinned: `upstream.lock.json` records the outer Firefox-WASM
commit, its Gecko fork commit, the Emscripten version and the adapter ABI. The
current build targets Linux and requires Git, Python 3, Node.js, pnpm, GNU make,
Rust **1.95** with `rust-src` and the `wasm32-unknown-emscripten` target, zstd,
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
git -C /path/to/build/firefox-wasm diff  # Review the patch before building.
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
close/reset during initialization, worker cleanup and input, before registering
it in the desktop. Update the app asset manifest and builder limits as needed
for the actual engine files, and verify CSP and cross-origin isolation on the
target desktop. The current live desktop blocks the adapter's blob script
loading. Do not weaken the whole site's policy without an appropriate review.

Online browsing is a separate step: configure only an authenticated Wisp relay
with server-enforced destination and resource policies, and test TLS and access
controls. The current `wispURL` is `null`; the v86 relay is not automatically a
Wisp relay. Never commit runtime binaries, downloaded toolchains, profiles,
credentials or user data.
