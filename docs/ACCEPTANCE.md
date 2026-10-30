# Real-engine acceptance gates

**All gates below are NOT RUN in this handoff.** The offline adapter tests listed in `TEST_STATUS.md` are separate evidence. Do not convert these to PASS because the unit tests passed.

For each run record: adapter archive hash, both source commits, patch hash, engine artifact hashes, build commands/compiler versions, host OS, browser/version, headers, relay configuration, observed result, logs and failures. No fabricated screenshots or success records.

## A. Build and baseline runtime

| ID | Required observation | Initial status |
|---|---|---|
| B01 | Exact wrapper and inner Gecko source pins obtained without overwriting existing projects | NOT RUN |
| B02 | Review native diff; verify ABI offsets/static assertions and actual navigation signatures | NOT RUN |
| B03 | Engine and new native file compile/link; raw artifacts, lifetime exports and data package match | NOT RUN |
| B04 | Manifest hashes match staged bytes; missing/altered artifacts fail visibly, no fallback renderer | NOT RUN |
| B05 | Real Chrome/Chromium harness reaches native READY in an owning Worker; no required `document` import crashes | NOT RUN |
| B06 | Home document displays from actual Gecko; normal host DOM contains only toolbar/canvas, not guest HTML | NOT RUN |
| B07 | `fixtures/engine-smoke.html` passes its own JS/CSS/canvas interactions; inspect failures individually | NOT RUN |
| B08 | Rendering works without an iframe, mirrored DOM, remote renderer or fake screenshot | NOT RUN |

## B. Interaction and navigation

| ID | Required observation | Initial status |
|---|---|---|
| I01 | Mouse down/up/move, hover, wheel, context action and guest focus work with coordinate scaling | NOT RUN |
| I02 | Basic ASCII, Unicode keys, modifier shortcuts, key repeats and blur releases behave consistently | NOT RUN |
| I03 | Typing goes only to focused window; Ctrl+backtick can return to toolbar; document IME limits | NOT RUN |
| I04 | Resize does not corrupt frame dimensions; zoom/DPR/layout limits recorded | NOT RUN |
| I05 | Native back/forward/reload/stop and actual-URL reporting work with two local documents and fragment history | NOT RUN |
| I06 | Failed navigation is visible and recoverable; native timeout instead fails that instance and requires reset | NOT RUN |
| I07 | Imported UTF-8 HTML runs in guest FS, not host; sibling files absent as documented | NOT RUN |
| I08 | Title/address cannot be spoofed via the page changing its JavaScript globals or text | NOT RUN |

## C. Per-window lifetime and availability

| ID | Required observation | Initial status |
|---|---|---|
| L01 | Two mount calls return synchronously and produce genuinely independent engine/page/profile state | NOT RUN |
| L02 | Closing middle window among three leaves other windows/terminal/desktop services functioning | NOT RUN |
| L03 | Close during asset fetch, native boot, document load and normal execution prevents late UI updates | NOT RUN |
| L04 | Repeated dispose is harmless; engine reset discards only its old instance | NOT RUN |
| L05 | Verify all nested pthread workers, relay connections and recurring tasks disappear after close | NOT RUN |
| L06 | Infinite guest loop can be reset/closed without hanging desktop; record descendant cleanup | NOT RUN |
| L07 | Repeated open/close reaches a stable resource baseline; measure real memory/worker counts, not DOM counts | NOT RUN |
| L08 | Hidden/minimized app reduces frame work; continued guest timers/networking are visible/documented | NOT RUN |
| L09 | Queue pressure preserves key/button order or fails the instance, never silently loses releases | NOT RUN |
| L10 | Multiple windows' resource requirements are measured; desktop admission policy reviewed if necessary | NOT RUN |

## D. Network and security qualification

| ID | Required observation | Initial status |
|---|---|---|
| S01 | With no relay, no public fallback WebSocket/network transport opens; offline document works | NOT RUN |
| S02 | Authorized relay handshake/TLS works; unauthenticated/unauthorized users are rejected | NOT RUN |
| S03 | Server-side destination policies block disallowed IP ranges, ports, DNS rebinding and metadata endpoints | NOT RUN |
| S04 | Valid/expired/untrusted/mismatched TLS certificate cases behave correctly without bypasses | NOT RUN |
| S05 | Guest cookies/storage separate from host; reset removes intended guest state | NOT RUN |
| S06 | Inspect all custom host imports for code evaluation, credential access and browser-API exposure | NOT RUN |
| S07 | Outer sentinel/host services unavailable to ordinary guest scripts; this is not an exploit-proof claim | NOT RUN |
| S08 | Audit upstream disabled protections and document the exact accepted threat model/configuration | NOT RUN |
| S09 | Header/CSP integration does not break adjacent apps, authentication or existing embeds | NOT RUN |
| S10 | Page content cannot initiate privileged desktop file/session/network operations | NOT RUN |

## E. Target-desktop acceptance

| ID | Required observation | Initial status |
|---|---|---|
| D01 | Register using real loader; no invented registry/host API, no app framework replacement | NOT RUN |
| D02 | Check actual open/close/minimize/resize/focus lifecycle beside existing apps | NOT RUN |
| D03 | Record representative site compatibility failures, unsupported audio/GPU/IME/accessibility features | NOT RUN |
| D04 | Confirm temporary-profile data-loss warning and no misleading “private/secure” guarantees | NOT RUN |
| D05 | Source/license notices and required corresponding source prepared before binary distribution | NOT RUN |

## Suggested fixtures, not benchmark claims

Start with the bundled self-contained HTML. Then use two pages on a controlled HTTP/HTTPS origin to test stylesheets, relative script imports, images, redirects, fetch, history and form submission. Only after relay policy tests should you try selected public sites. Do not use personal accounts.

Test hostile or broken inputs in a disposable build: huge allocation, blocked JS, malformed asset metadata, invalid URLs, rapid focus/input switching, rapid resize and close while loading. Keep expected failures recorded. The purpose is to find integration defects, not to demonstrate a single working screenshot.
