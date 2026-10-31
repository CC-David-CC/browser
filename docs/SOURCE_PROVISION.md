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
the newer candidate uses source snapshot `adece7482`, SHA-256
`2e64c1c3856f622af986157059eca6f8f14a8c73e275829d397372b70701c127`.
These snapshots are retained at `/browser-sources/`. This does not mean
that either desktop candidate has been deployed. The newer snapshot
`codi-browser-source-2ed6d0259.tar.zst`, SHA-256
`49f1c63f6160a58d9d6624d5baa35589fae1a74580f32cbb8883f71f9a203b0b`,
includes the currently running relay sources from commit `6078c8e18` and
the current tracked Browser app. It was downloaded from the public route
and hash-verified after publication. The older relay snapshot at commit
`05e70e3b0` remains available, SHA-256
`6031d72c1c102de2260a634e9e1b8b559f8cccf292b6512e9270e348f2df5ef9`.
The current desktop candidate has newer Browser source snapshot
`codi-browser-source-0488c275e.tar.zst`, SHA-256
`841993d069a9d824942224b2e34012a1dc56ce6c24f3407b920adaa4f2d7e0cd`;
its public download was also hash-verified. The candidate is not yet live.
The current relay and newer desktop candidate are represented by
`codi-browser-source-802621ec2.tar.zst`, SHA-256
`128c33ee16a6dde95f5c594b19ef6c8a05cb9b251024e95ac859f888b3a26c90`,
which was independently fetched and checked from the public source page.
The engine's built output and generated archives do not belong in Git.

The notice page provides the generated Gecko license inventory, Emscripten
runtime notices, Liberation Sans font license, Wisp AGPL and adapter MIT text, and links to the pinned
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

The build's Gecko-generated license page lists SoundTouch, FFmpeg and Libav as
LGPL possibilities. Inspection of the actual `libxul.stripped.so` defined and
undefined symbols found no defined SoundTouch implementation: the fourteen
`RLBoxSoundTouch` references are unresolved. `libgkcodecs.stripped.so` showed
no defined `avcodec_`, `avformat_`, `avutil_` or SoundTouch symbols in the same
inspection. This is evidence about these symbols, not a complete link inventory
or a legal conclusion. Complete linked-component and LGPL review still remains.
The Mozilla build in this pinned revision does not recognize `mach sbom`;
the current upstream SBOM documentation describes a newer tooling capability,
so its output cannot be assumed to describe this build.

The built `gecko.data` stages four Liberation Sans TTF files from Firefox's
PDF.js tree. Their upstream `LICENSE_LIBERATION` (SIL OFL 1.1) matches pinned
source SHA-256 `93fed46019c38bbe566b479d22148e2e8a1e85ada614accb0211c37b2c61c19b`.
The exact notice is now included at `/browser-sources/emscripten-licenses.txt`;
the public response was hash-checked after publication. Notice generation
requires this exact license input.

The upstream link script explicitly links the embedder, libxul, libnss3,
libgkcodecs and Mozilla glue; its GRE staging script excludes shared libraries,
WASM files and dictionaries. The built but separately present `liblgpllibs.so`
and `libmozavcodec.so` contain SoundTouch and FFmpeg symbols respectively,
whereas the staged linked libraries do not define those implementations.
This is further evidence that those libraries were not linked by this script;
it does not replace a full inventory of every compiled component or settle
the remaining license review.

The actual `toolkit/library/build/libxul_so.list` contains 1,860 object
entries. Its identifiable third-party groups include ICU, Abseil, msgpack,
zstd, dav1d, libjpeg, libmkv, libnestegg, libpng, speex resampler, libwebp,
libyuv, and libcubeb. ICU's notice is in the generated Firefox notice page.
To avoid relying on generic license headings for the other named libraries,
the public runtime notice file now also includes their license files from the
exact pinned Firefox revision, including both libjpeg-turbo's license and the
IJG README it references. `tools/collect_component_notices.py` recreates this
set; SHA-256 of its output is
`85201fadf7d77201dc1d8c026f0340ecd6b258f6d63fe339486a200d3e377dde`.
The public combined notices match SHA-256
`4d04c982f8713a75b6c787679e0f93ff7ac076b08c5fd5ce0d82da515bf6d35e`.
This group-level review is not a complete audit of all 1,860 object inputs,
Rust dependencies, generated resources, or downstream legal requirements.

The actual target Cargo fingerprint directory contains 477 distinct names;
335 match vendored Rust package names. `tools/collect_rust_notices.py` collects
the declared licenses and available license/notice files for all matching
vendored package versions, yielding a conservative set rather than an exact
final-link inventory. The package contains 38 matching vendored versions
without separate top-level notice files; their declared licenses and source
remain listed. A subsequent tracked-workspace manifest scan matched 131 of
the other 142 names to Firefox source packages, leaving 13 names unmatched
across the full tracked manifest scan (the scans use different file-selection
rules). These include Rust standard-library and compiler crates. The build used
Rust 1.95.0, commit `59807616e1fa2540724bfbac14d7976d7e4a3860`; its standard
library copyright and dependency notice HTML is appended unchanged to the
public combined notice. Some workspace manifests omit a license field;
all tracked Rust files under the 22 matched manifests carry Mozilla license
headers (47 observations, including overlapping paths). The reproducible
check is `tools/audit_workspace_headers.py`; metadata and non-Rust files were
outside its scope. This does not establish which target-built crates survive final
linking. The Rust crate notice input SHA-256 is
`8e8bafa0d9f2f3243d1e02910c9b9fd270c24f9c357aa3fcafcb3be8a4a60712`;
the public combined notices now match
`cfec82baaa9cc83eb238288f493d2116a14603c34aadebab15c7796c4d7cd9c3`.
The reproducible manifest scan is `tools/inventory_workspace_crates.py`.

Two target-built vendored audio crates, `pulse` and `pulse-ffi`, declare ISC
and refer to an accompanying license absent from their vendored directories.
Firefox's Cargo.lock pins upstream `mozilla/cubeb-pulse-rs` revision
`3cf4a1af09a1748d0e184297a17132bdcc608874`. Its root LICENSE was fetched at
that exact revision, SHA-256
`44c6b5ae5ec3fe2fbc608b00e6f4896f4d2d5c7e525fcbaa3eaa3cf2f3d5a983`,
and is included in the combined public notices. The crates' source files also
retain their original copyright headers. This covers the observed missing
file without claiming that all remaining license questions are resolved.

The source archive corresponding to the deployed file-mirror update is
`https://ksu.codes/browser-sources/codi-browser-source-485928f3f.tar.zst`,
SHA-256 `e3d823eeb3d042ca051f7b12c2c775a945660036c7ec3ca55bd07588e32bf968`.
It is linked from the public source index; this update does not resolve the
remaining audit limitations described above.

The clicked-download release additionally distributes its modified Mozilla
modules and Browser adapter in
`https://ksu.codes/browser-sources/codi-browser-source-29a71d717.tar.zst`,
SHA-256 `f231dfee54279c20c6bca77988b556d6fcad7c8886792eb78c63e1f9c10b680b`.
The pinned upstream Firefox source archive and earlier notices remain linked.

The source for the staged audit-capable relay runtime is published at
`https://ksu.codes/browser-sources/codi-browser-source-f4a43b30e.tar.zst`,
SHA-256 `3e090e5a9508f0ff53aae97791ff21c71dc38afb5d84bc9cc2cc54f304aeb42c`.
Publishing source does not by itself enable server recording.

The Browser frontend memory-growth fix is represented by
`https://ksu.codes/browser-sources/codi-browser-source-ee1704dcd.tar.zst`,
SHA-256 `0ef62be5518d9cbd01543efd9bacafc22238ac6b4ca7a00719898753cfbab60a`.

The built `libxul_so.list` includes `config/external/rlbox/rlbox_thread_locals.o`,
whose source includes RLBox headers. Firefox's generated license page names
`third_party/rlbox`, but the separately bundled notices did not reproduce its
specific copyright. The exact pinned `third_party/rlbox/LICENSE` is now also
included in the public combined notices. Its SHA-256 is
`891d419ba95ab39090775820f4178421dbdcd241c080003aa44f62445a48615a`;
the public combined notice SHA-256 is
`28b3c6267097ecfa2e40dc56de5715348ca011652a2b26817f7cbba15e2570b7`.
Recreate the extra input from the pinned checkout with
`git show 2e1e835a5da5907e5ceef19aade58a7493f1e34d:third_party/rlbox/LICENSE`,
and supply it to `prepare_notices.py --rlbox-license`. This addresses the
identified attribution gap; it does not establish a complete final-link audit.

A further pass over all 1,860 entries grouped object paths beyond `media/` and
`third_party/`: the list includes ANGLE, Skia, Cairo, FreeType, protobuf,
Brotli, Expat, Graphite, HarfBuzz, WOFF2, Snappy, Chromium and jsoncpp.
`tools/collect_graphics_notices.py` collects the corresponding license files
from the exact pinned Firefox checkout; its output SHA-256 is
`a447f4de3c0b4b60c6bf707811d89a9f8a5ec0e7297eb0e82573ea196b06196e`.
Cairo's upstream file describes LGPL 2.1 or MPL 1.1 choices; both included
license texts and the full pinned Firefox source remain available. FreeType's
pinned `moz.yaml` names release `VER-2-14-2` and the FreeType License; Firefox
omits the upstream `docs/` directory. The exact release's `docs/FTL.TXT`,
SHA-256 `5a5ee54c5001bbad1cdc1a57cc3dd4c42199b2da09d39c7ee41fab002d02967f`,
is included along with the license information in Firefox's source. The
FreeType 2.14.2 attribution appears on the public source and notice page.
The expanded combined notice has SHA-256
`35258b272eca7cb0f23e53c847733c536197ee3ce8884b66d693b425433b6d1a`.
To rebuild, supply the collected output as `--graphics-notices` and the
release's FTL text as `--freetype-license` to `prepare_notices.py`. This is
additional object-group evidence, not a complete object-level legal audit.

For Rust packages missing separate notice files in Firefox's vendored copies,
a review compared 26 registry packages against the exact SHA-256 checksums in
the pinned Firefox `Cargo.lock` (lockfile SHA-256
`1617a3c654395fa24543a12b4eb95c62700f1b75f5d439b8cd1b93ffc7404b03`).
Twenty-five had no root license file in the published crate. `remove_dir_all`
had two files named `LICENCE-APACHE` and `LICENCE-MIT`, which the original
collector missed because it only matched the spelling `LICENSE`. The collector
now recognizes both spellings. One nested debug-tree
license belonged to Asciidoctor documentation and was not treated as the
crate's own license. The packages' `.cargo_vcs_info.json` revisions and the
lockfile's pinned Git revisions were used to inspect their original source
repositories. The resulting 27 additional license files from 16 pinned
repository revisions are listed with per-file hashes in
`RUST_UPSTREAM_LICENSES.json`; the collector verifies those hashes before
including them. The combined input SHA-256 is
`c751b4624a249a286f732ca2494c8d3e3f9ae108f67dded1fd2970cef30439e5`.
The public combined notices are SHA-256
`7775f6197a7a14a397ad6180b43b4c553aaacef77ac4e0136a34fc15f3f3f829`.
Some upstream repositories had no separate license file at the pinned
revision, and the svg_fmt repository revision was unavailable; those are
not represented as resolved. Other non-GitHub sources also remain outside
this collection. Cargo fingerprints show target builds, not necessarily
objects retained by the final linker.

The corrected target Rust notice input, including the two previously omitted
`remove_dir_all` files, hashes to
`8c083caaa5a59ab1a01c0239ca82e378f4e9868b91f6c746a4f711ccea9444eb`.
`tools/audit_missing_rust_crates.py` and `RUST_MISSING_REGISTRY.json` reproduce
the registry-archive checksum and filename audit without extracting archives.

The Browser also distributes unmodified Noto Sans Arabic Regular and Noto Sans
CJK Regular fonts, under the SIL Open Font License 1.1. Their copyright and
license notices ship as `engine-fonts/NOTO-CORE-LICENSE.txt` and
`engine-fonts/NOTO-CJK-LICENSE.txt`. Run `python3 tools/prepare_fonts.py` in the
Browser app before building: it checks installed fonts by SHA-256 or downloads
the exact Ubuntu packages and verifies both package and extracted font hashes.
These assets add approximately 19 MiB to the first Browser app load and are
cached normally. The CJK collection supports several regional faces; it is not
a promise of font coverage for every writing system.

The language-font release's Browser integration source is published at
`https://ksu.codes/browser-sources/codi-browser-source-f70a64aa3.tar.zst`,
SHA-256 `1772fa4cc0e5ec205a163b9e6467ba18ffabf782e6c3a38f62316e9ad84f520d`.
The archive is listed on the public source index. The exact font assets and
notices ship with the Browser bundle; the archive contains the reproducible
font staging instructions and SHA-256 pins, not generated font binaries.
