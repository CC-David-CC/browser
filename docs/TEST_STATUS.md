# Browser test status

As of the live Simplified test on 2026-10-31, the Browser app and its Gecko
engine are deployed at ksu.codes. Registered-account tests have exercised
network admission, blocked destinations, saved downloads, browser/server file
sync, re-sign-in, rule changes, and recovery. Desktop and phone-sized Chrome
layouts have been tested; the latter is emulation rather than a physical phone.
See `SIMPLIFIED_HANDOFF.md` for specific live releases, evidence and limitations.

The live Applications menu now labels Browser “in development” and disables its
launcher while higher-priority STEM apps are improved. The app source, engine,
relay integration and already-open Browser windows remain in place. The save,
replace and reset themed-dialog update below is local only and is not in the live
Browser bundle.

On 2026-10-31, the Browser app's save-name, replacement, and reset prompts were
changed to the desktop's themed dialogs. An isolated real-engine workflow passed
at 1366×900, emulated 412×915 phone size, and 3840×2160. It covered download to
My files, cancellation, replacement, synchronization, stale-write protection,
reset cancellation/acceptance, and the absence of browser-native dialogs. This
source update has not yet been deployed to ksu.codes; physical-phone input was
not tested.

A fresh desktop live-site check rendered example.com and the McMaster-Carr
catalog. Grainger displayed its own “Access is temporarily restricted” page.
The reason for that external restriction is not established. These observations
do not guarantee compatibility with other sites or future changes to these
sites. The engine's complete linked-component licensing review remains open.

The status “Navigation requested” means Gecko accepted the navigation command;
it does not confirm the page has finished loading or that the destination
accepted the request. The current native status interface reports the current
URL and back/forward availability, not a load-completion event. A reliable
completion or HTTP-error indication needs an engine-side progress signal and a
newly qualified engine build. For now, inspect the page itself and any separate
network-policy message rather than interpreting that status as a success check.

An isolated experimental engine queried `nsIWebProgress::GetIsLoadingDocument`
through the docshell. It compiled and linked, but did not provide a reliable
loading signal in a real Gecko/Wisp test: the fixture received the request and
held the HTTP response for eight seconds, while repeated one-second status
samples all reported `false`. The experiment was not deployed. A progress
listener or another authoritative signal needs its own verification; neither a
changed URL nor this flag alone proves navigation has finished.

A subsequent diagnostic progress-listener build observed a matching completion
after a delayed response and a nonzero result for a blocked connection. An
HTTP 404 nevertheless returned a zero Gecko network result, so that result
cannot by itself indicate a successful HTTP page. The prototype is unshipped;
see `experiments/README.md` for evidence and remaining checks.

Another unshipped prototype read the HTTP channel and distinguished a fixture
200, 404 and redirect to 404. A separate slow-response test with the shipping
engine showed that Stop remained queued during the first four seconds of a
ten-second response delay. It needs a responsive cancellation path before Stop
can be relied on during a stalled navigation.

An isolated cancellation prototype subsequently stopped the delayed fixture
in 68–85 ms across three runs, handled immediate Stop and later navigation,
and kept a second Browser window independent. It is not in the live engine;
the pairing, lifecycle and failure tests described in `experiments/README.md`
remain before it can replace the shipping implementation.

## Historical source handoff 0.1.0

The following report describes the earlier source-only handoff and is retained
for historical context; it does not describe the currently deployed system.

Recorded: 2026-10-30.

**The browser application is not yet tested in a browser or in the target desktop. Gecko and the native patch have not been compiled or run here.**

## Checks actually executed

Environment: Node v22.16.0; Python 3.13.5; Linux container.

| Check | Result | What it establishes |
|---|---|---|
| JavaScript `node --check` across adapter, tests and tooling | PASS | Parser accepts source; no browser runtime validation |
| `bash -n` for shell tools | PASS | Shell syntax only |
| Python source compilation | PASS | Python syntax only |
| Loopback HTTP server smoke check | PASS | HTML 200, JavaScript MIME, isolation/CSP headers, hidden-file 404 and missing-engine-manifest 404; no browser or WASM execution |
| `node --test tests/*.test.mjs` | 79 passed, 0 failed | Policy, synthetic mailbox, fake-worker lifecycle and static contract tests |
| `python3 -m unittest discover -s tests -p 'test_*.py' -v` | 7 passed, 0 failed | Patch transforms on synthetic anchors; no native compilation |

Reproduce these checks with `bash tools/check.sh`. They require no package install, network access or Gecko build. The fake worker and synthetic shared memory are isolated test fixtures, never runtime fallbacks.

## Not executed / not established

- Fetch/build of the full pinned Gecko source and toolchain in this environment.
- C++ compilation or linking of `native/embed-host.cpp`.
- Raw engine/pthread initialization inside the owning Web Worker.
- Home or smoke-page rendering by Gecko.
- Real user input, navigation, JavaScript execution, network traffic or TLS.
- Multiwindow isolation, actual descendant worker teardown, persistent memory behavior.
- A Wisp relay configuration or deployment.
- The real desktop's app loader, files, session, networking, UI or security policies.
- Security audit, web-platform conformance, performance benchmark or accessibility validation.

All acceptance rows in `docs/ACCEPTANCE.md` remain NOT RUN. The generated manifest deliberately labels builds `runtimeTested: false`; successful source tests/staging do not change that automatically.

## Scope of the delivered archive

This is code and build tooling, not a prebuilt browser release. `engine/` has documentation but no engine binaries or manifest until a build is completed. The current app reports that missing dependency honestly. Do not replace that error with simulated content and call the engine tested.
