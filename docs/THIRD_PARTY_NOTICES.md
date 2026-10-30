# Third-party source and distribution review

This source ZIP contains original adapter code, not the fetched upstream browser, its binaries, fonts or website assets.

The build workflow fetches:

- **HeyPuter/firefox-wasm** — upstream wrapper/build/embedder project, MPL-2.0. Pinned in `upstream.lock.json`.
- **HeyPuter/firefox** — Mozilla-derived Gecko/SpiderMonkey fork, MPL-2.0 and its bundled third-party notices/licenses. Inner revision pinned separately.
- **Emscripten and its toolchain/dependencies** — preserve their licenses; the upstream build patches its WasmFS runtime.
- **@mercuryworkshop/wisp-js** and upstream pnpm dependency graph — preserve exact resolved packages and their licenses. Inspect the upstream lockfile/license files before redistribution; this handoff does not assert one blanket license for them.

The native extension is original MIT adapter code compiled alongside the upstream embedder. Edits made by the patch script to upstream files remain subject to those files' original licensing. Do not replace upstream copyright headers. When distributing compiled output, preserve required notices and make the corresponding modified covered source available as required by applicable licenses.

This handoff is not a legal determination of distribution compliance. Do not treat the adapter's MIT license as permission to relicense all Gecko or omit its source/notice obligations. Do not imply Mozilla endorsement or use Firefox branding without reviewing the relevant trademark terms.

The build may stage resources from the upstream GRE. Review resource licenses before shipping; this ZIP does not supply font files. Source URLs and exact inspected paths are in `docs/SOURCES.md`.
