# Navigation progress experiment

`navigation-progress-debug.patch` is an unshipped diagnostic prototype for
the pinned Gecko build. It attaches a weak-reference-capable
`nsIWebProgressListener` and exposes event counters and the request name in the
existing status JSON. It must not be shipped as-is: the request name can contain
paths or query data, and registration, redirects, overlapping loads, lifetime,
and HTTP response handling need a production design and tests.

In an isolated Gecko/Wisp test on 2026-10-31, the fixture held a successful HTTP
response for eight seconds. After the listener was attached before navigation,
the matching request produced start and stop events, with the stop observed only
after the response. A policy-blocked navigation produced a nonzero Gecko result
and the existing policy-denial message. A fixture HTTP 404 produced a stop event
with Gecko result zero: that result means the network operation completed, not
that the HTTP response was successful. UI status must not equate it to success.
The listener's start and stop may both occur between one-second status polls;
checking only the latest state loses the start event. The first attempt also
navigated before the listener attached, and a later test initially reused old
fixture counters; both were corrected before the observations recorded here.

The debug candidate WASM had SHA-256
`f38b4055f3c5cc918cb3102c9218051d391db2ae3f0d7dd7184c20a87f066763`.
No candidate was deployed; generated builds and fixture processes were removed.
Next, investigate HTTP channel response status and request association, test
redirects, cancellation, DNS/TLS failures, multiple rapid navigations, and avoid
exposing path/query metadata outside what the UI needs. Only then consider a
new engine build, source publication and live rollout.

The later `navigation-http-debug.patch` also queries the HTTP channel. An
isolated real Gecko/Wisp test observed 200, 404, and the final 404 after an
HTTP redirect. The candidate remains diagnostic, exposes full request names,
and is not deployed. It has not established correct handling of rapid
navigations, TLS failures or every redirect shape.

The same local fixture exposed a separate limitation in the **shipping**
engine: while an HTTP response was delayed for ten seconds, clicking Stop did
not complete during the first four seconds and the status remained “Loading…”.
The engine command queue processes one native call at a time; `xul_load` spins
until a new document becomes interactive, so the Stop command waits behind
that call. A responsive cancellation mechanism needs coordination between the
worker and native loop; do not assume that a progress-listener change fixes it.
The local fixture deliberately maps a test hostname to loopback and must never
be deployed as a production relay.

## Stop prototype

The three `navigation-cancel-*.patch` files are a matched, **unshipped**
prototype. The worker signals an in-flight load through an atomic mailbox
field and removes queued loads when Stop is requested; the modified native
event loop consumes that signal and asks Gecko to stop. The worker must not be
deployed with the old engine: the old engine does not consume this signal.

With the patched engine and worker in an isolated app, three repetitions
stopped a ten-second delayed response in 68–85 ms and successfully navigated
afterward. Immediate Stop also returned, and a separate two-window test found
that stopping one window did not disrupt the other. The reusable local-only
fixture and tests are `tests/browser-stop-experiment-fixture.py`,
`tests/browser-stop-experiment.test.mjs`, and
`tests/browser-stop-isolation-experiment.test.mjs`. The fixture requires
`CODI_EXPERIMENT_APP` to point to the isolated patched app and deliberately
maps a synthetic host to loopback; never serve it publicly.

This is not yet a production patch. Before rollout, integrate the native
change into the pinned patch/build/source-provision pipeline, add explicit
ABI/capability pairing, test cancellation when Gecko's event loop is idle or
stalled, repeated and overlapping commands, window closure, phone behavior,
and failures. Ensure the UI reports cancellation only after the engine has
actually processed it. The experimental WASM SHA-256 was
`13a8022769bfb2486471515d40e9af40df11ff901b2ac2bf4f4dd5b64b954828`.

## Integrated candidate (not deployed)

The prototype is now integrated into `tools/patch_engine.py` and paired with
`browser-gecko-mailbox-v2`; both the manifest and the native exported ABI must
match the worker. An isolated build from the pinned revisions produced WASM
SHA-256 `23b02f87791ad87208faf3680c5269ce0a7dc77c7bf33c7f88986e52d2ea5e2b`.
Against this exact build, a slow-response Stop completed in 68 ms, subsequent
navigation and immediate Stop worked, and a clean-fixture two-window test
showed that stopping one window did not disrupt the other. A phone-sized
emulated layout also passed Stop, and closing the window during a later slow
load followed by reopening worked. This is not a physical-phone test or proof
that a completely stalled Gecko event loop can process cancellation. Unit
tests cover refusing an incompatible manifest and only signaling active loads.
Before shipping, publish the corresponding v2 source and native patch, complete
the remaining failure/lifecycle review, and verify the built deployment live.

The integrated ABI v2 build described above was subsequently deployed in
release `8d5fe713698d4bb94781b10ef22c4815e48b1d046237730e23259945d2332f05`.
Its source package is available via the authenticated Licenses & source page.
The packed bundle independently passed the delayed-response test in 67 ms;
live desktop and emulated-phone sessions rendered example.com, and live Stop
returned in the phone-sized session. The progress-listener prototypes remain
unshipped; page-completion/error reporting is a separate outstanding issue.

## Event association investigation — 2026-10-31

`navigation-trace-debug.patch` is a local-only diagnostic for the deployed
ABI v2 source. It records bounded numeric request identifiers, event flags,
network results and HTTP codes; it does not record request URLs. Do not deploy
it: the identifiers expose implementation details, and the status API and
listener lifetime have not been designed for production. The debug build's
WASM SHA-256 was
`6763988757faf62ddc583a6ba69ed2ca19f5bad3c777525855de034f8a8660c4`.

`tests/browser-progress-diagnostic-fixture.py` is an explicitly loopback-only
fake-auth fixture; it must never be exposed as a production relay. The matching
`tests/browser-progress-diagnostic.test.mjs` exercised real Gecko/Wisp with
200, 404, an HTTP redirect ending in 404, a script redirect ending in 404,
Stop during a stalled response, a later successful request, a blocked
hostname and a deliberately closed TLS connection. All assertions passed.

The observations constrain the design:

- Normal HTTP 200 and 404 both reported network result zero; the latter had
  HTTP status 404. An HTTP redirect reported the final 404.
- The start and successful stop events had different request identifiers, so
  matching those pointers would incorrectly lose successful loads.
- A script redirect produced a stop with the same cancellation result as an
  explicit Stop, alongside HTTP 200, before the next request reached 404.
  Treating every cancellation as a failure would mislabel ordinary redirects.
- The blocked destination and the closed TLS connection reported the same
  network result in this fixture. A network result alone cannot identify the
  cause; preserve the relay's separate, bounded policy-block notification.

The first TLS test timed out because the fixture waited for an HTTP header on
an incoming TLS connection. It was corrected to close that connection, then
rerun; the timeout was a fixture defect, not an engine result. Further work
must associate events with the current top-level navigation, handle overlapping
and page-initiated navigations, distinguish an explicit Stop from redirect
cancellation, and avoid exposing request data. Keep the current neutral status
until those behaviors are verified.

For reproducibility, apply the diagnostic patch only in a clean, isolated
copy of the native source, rebuild and stage a matched engine with the pinned
build tools, then use `tests/prepare-browser-progress-diagnostic.py --engine
STAGED_ENGINE --out NEW_DIRECTORY`. Set `CODI_EXPERIMENT_APP` to that output
and run the fixture, then run the diagnostic test with Puppeteer and a local
Chrome debugging endpoint on port 19255. The preparation script adds
instrumentation only to the copied worker and verifies its source anchors.
