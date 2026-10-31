# Browser engine source provision, 2026-10-30

The Gecko engine is built from Firefox-WASM `bc69aaa5e2c5388bcf93a43b975b490bb940f4c0`,
with the local modifications applied by `tools/patch_engine.py`, and Firefox
`2e1e835a5da5907e5ceef19aade58a7493f1e34d`. The Firefox checkout was clean
when the source archive was produced. The Firefox-WASM archive plus its patch
was extracted and compared byte for byte against the three modified tracked
files in the build checkout; the additional `embed-host.cpp` was also compared.
The engine manifest records this additional file's SHA-256 as
`13080154869cf68b07186c19dfc9891f3c85246ad7a6e721fd8fce549dde5e03`.

The following source archives were prepared on r730, their Zstandard streams
were verified, and copies were hash-checked on box-webhost in
`/srv/codi-browser/source-staging/engine-6736dce5/`. The allowlisted archives
and notices are served at `https://ksu.codes/browser-sources/`; these large
generated artifacts are not Git inputs:

| File | SHA-256 |
| --- | --- |
| `firefox-2e1e835a.tar.zst` | `85618173c479db5432a046b86e94bec24f5edba14013390fbf50ad86c7e688cb` |
| `firefox-wasm-bc69aaa5.tar.zst` | `1c2cea6cd55f317fb196b389d5580f2d783296ecd13af4765c2b1e491d2bc57c` |
| `firefox-wasm-local.patch` | `63effdb856f86dad6995efe99a4d520694e4c9234a279e6ff3c0f6cf3131df8c` |
| `embed-host.cpp` | `13080154869cf68b07186c19dfc9891f3c85246ad7a6e721fd8fce549dde5e03` |
| `emscripten-6.0.1-patched-source.tar.zst` | `0ef04153b359fc83a6222c44aebeb32b9ad96e36362720c958f0d2e97b7ad818` |
| `wisp-js-0.4.1-source.tar.zst` | `3f5ed9fd60dfab9fecef30ce6877f436eb4895a096873e551c2fb4cb13f08557` |

The Emscripten archive contains the patched build checkout, excluding caches,
`node_modules` and Python bytecode. The Wisp archive contains the exact
installed package's source, package metadata, README and AGPL-3.0 license.
An additional archive of the Codi Browser app and its related integration
sources was made from Git commit `59dfaf024` with SHA-256
`00e499a9c5e8c812666616023f4d02e98f49696b7fc7d85040123a93ebe0ea34`.
The desktop release candidate uses source snapshot `0fc6bf9a7` with SHA-256
`47ac4d287646b42b808680e2be422e4a7a7bf62dcd928b6ae911bf4a2c91bbe4`;
both snapshots are retained at `/browser-sources/`. This does not mean that
the desktop candidate itself has been deployed.
The running relay's source snapshot is commit `05e70e3b0` with SHA-256
`6031d72c1c102de2260a634e9e1b8b559f8cccf292b6512e9270e348f2df5ef9`.
The engine's built output and generated archives do not belong in Git.

The notice page provides the generated Gecko license inventory, Emscripten
runtime notices, Wisp AGPL and adapter MIT text, and links to the pinned
archives. `tools/prepare_notices.py` reconstructs that page from the exact
build inputs. Mozilla's
[MPL 2.0 distribution terms](https://www.mozilla.org/en-US/MPL/2.0/) and
[FAQ](https://www.mozilla.org/en-US/MPL/2.0/FAQ/) describe its source and
notice requirements. Wisp's AGPL-3.0 terms are separate; review the complete
bundle and corresponding source obligations. Firefox and the build toolchain
include many third-party components and licenses, so these snapshots alone do
not establish that all notices or source provisions are complete. Confirm the
actual linked component inventory, including any LGPL obligations, before
public engine deployment. The observed engine link reported 37 unresolved
symbols, including file-picker and audio functions; this is a separate
functionality limitation that requires investigation before promising ordinary
website compatibility. Update the source archive whenever the shipped Browser
source or engine build changes.
