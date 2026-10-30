# Inspected primary sources and provenance

Reviewed online on 2026-10-30. These sources informed the adapter; they do not establish that this adapter was compiled or executed. The runtime/source revision is pinned, not inferred from a future latest release.

## Engine upstream

Project: https://github.com/HeyPuter/firefox-wasm

Wrapper/build commit: `bc69aaa5e2c5388bcf93a43b975b490bb940f4c0`

Pinned tree: https://github.com/HeyPuter/firefox-wasm/tree/bc69aaa5e2c5388bcf93a43b975b490bb940f4c0

README: https://github.com/HeyPuter/firefox-wasm/blob/bc69aaa5e2c5388bcf93a43b975b490bb940f4c0/README.md

The README identifies Gecko compiled to WebAssembly, Wisp transport, Linux builds, Emscripten 6.0.1 and the experimental JS-to-WASM JIT. This handoff disables that JIT rather than assuming it is ready.

## Specific inspected interfaces

All paths below are under the pinned tree above.

| Path | Used for |
|---|---|
| `Makefile` | Inner Gecko pin, Rust/Emscripten build prerequisites, object-directory/build workflow |
| `gecko.js/js/index.ts` | Existing factory/preRun parameters, native mailbox use, frame/input handling; inadequate runtime teardown in public destroy wrapper |
| `gecko.js/src/embed-xul.h` | Actual wasm32 XulCmd layout and shared declarations |
| `gecko.js/src/embed-xul.cpp` | Mailbox state machine, allocation ownership, READY marker, software/GPU flags |
| `gecko.js/src/embed-browser.cpp` | Native document/docshell and navigation setup |
| `gecko.js/src/embed-init.cpp` | Profile/provider setup and security-related preference changes |
| `gecko.js/build-lib.sh` | Raw artifacts, MODULARIZE factory, worker environment, exported methods, memory/thread flags |
| `gecko.js/lib/wisp-net.js` | Injected Wisp client contract, disabled transport without URL/client, per-socket bridge |
| `gecko.js/lib/audio-out.js` | Host AudioContext/AudioWorklet dependency relevant to worker-only embedding |
| `gecko.js/lib/provider-fs.js` | Provider boundary; no host provider supplied by this adapter |
| `gecko.js/package.json`, `pnpm-lock.yaml` | Existing package/build dependency path; integration must preserve locked versions |

Direct raw interface examples:

- https://raw.githubusercontent.com/HeyPuter/firefox-wasm/bc69aaa5e2c5388bcf93a43b975b490bb940f4c0/gecko.js/src/embed-xul.h
- https://raw.githubusercontent.com/HeyPuter/firefox-wasm/bc69aaa5e2c5388bcf93a43b975b490bb940f4c0/gecko.js/build-lib.sh
- https://raw.githubusercontent.com/HeyPuter/firefox-wasm/bc69aaa5e2c5388bcf93a43b975b490bb940f4c0/gecko.js/js/index.ts
- https://raw.githubusercontent.com/HeyPuter/firefox-wasm/bc69aaa5e2c5388bcf93a43b975b490bb940f4c0/gecko.js/src/embed-init.cpp

## Inner engine native API

Repository: https://github.com/HeyPuter/firefox

Commit: `2e1e835a5da5907e5ceef19aade58a7493f1e34d`

Navigation interface inspected:
https://github.com/HeyPuter/firefox/blob/2e1e835a5da5907e5ceef19aade58a7493f1e34d/docshell/base/nsIWebNavigation.idl

The extension uses native back/forward/reload/stop/currentURI methods instead of injecting a script into page context. C++ compatibility is still uncompiled in this handoff.

## Evidence boundaries

A browser engine port being available is stronger evidence than a theoretical custom HTML renderer. It does not prove standards coverage, independent window lifetime, arbitrary-site compatibility or safe public deployment. Source inspection is explicitly separated from synthetic unit tests and actual runtime acceptance in the other documents.

The upstream memory flags (`INITIAL_MEMORY=536870912`, `PTHREAD_POOL_SIZE=20`) describe a build configuration, not a measured per-window memory benchmark. No timings or real-browser performance results were collected here.
