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
