# Engine assets are NOT bundled

This directory intentionally has no fake renderer and no placeholder WASM binary.
Build the pinned Gecko port with `tools/build_engine.sh`. It stages:

- `gecko.js`: **raw Emscripten glue**, not the upstream dist/ UI library.
- `gecko.wasm`: the actual Gecko + SpiderMonkey engine.
- `gecko.data`: the upstream runtime data package.
- `wisp-client.mjs`: a local bundle of the upstream-locked client dependency.
- `manifest.json`: ABI, source revision, byte sizes and SHA-256 values.

Without these artifacts the app reports an installation error rather than rendering
HTML in the outer browser. No files are fetched from a CDN by the shipped app.
The build tooling has not been exercised against the engine in this handoff.

Retain upstream licenses and provide corresponding source as required when distributing
built artifacts. Hashing your own build does not establish upstream authenticity.
