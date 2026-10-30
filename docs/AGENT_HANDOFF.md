# Integrator handoff — review before integrating

**Role:** You are the integrator who knows this browser desktop. I am supplying a best-effort plugin implementation from outside its repository. I have not tested it in a browser, compiled its native extension, or run it in the user's desktop. Treat it as reviewable source, not an approved drop-in release.

## 1. Preserve the actual goal

The user explicitly rejected a sandboxed iframe. They want an independent, complete HTML/CSS/JavaScript engine inside an app window, so ordinary websites do not implement the desktop's plugin contract.

This attempt targets real Gecko/SpiderMonkey using the HeyPuter Firefox-WASM port. It is not a newly invented browser engine. The host paints an engine framebuffer onto a canvas. It must not inject the guest document into the outer DOM, mirror guest HTML into the host, replace the guest engine with iframe/srcdoc, or silently route rendering to a server. The browser application implements `mount(host)`; the pages inside it do not.

Local networking may use a relay. Do not confuse that with remote rendering, and do not promise zero server bandwidth.

## 2. Verified integration contract versus assumptions

The only desktop contract established here is:

```js
export function mount(host) {
  const body = host.ui.make('div', 'window-content');
  return { element: body, dispose() {} };
}
```

`mount` is synchronous. Each call represents a separate app window. The returned `dispose()` must be safe more than once. Shared desktop services already exist; do not recreate Linux, the terminal, user sessions, a filesystem, peer networking or a new app base class.

No actual desktop registry/configuration source was available in this handoff. Do not copy a guessed service name into production. Inspect your app loader, existing adjacent applications, file-access grants, window-close path, CSP and resource ownership first. A historical project path was `/home/dflanag3/CodiServer/desktop-preview`, but discover the actual current checkout rather than assuming it.

Current code uses `host.ui.make` only. Other DOM creation uses the returned element's document. A ShadowRoot scopes the **browser toolbar's** CSS; it is not an iframe or the guest renderer, and is not claimed as a security boundary. Determine whether it fits the existing desktop's sizing, focus and styling conventions.

## 3. What is supplied

| Location | Purpose |
|---|---|
| `index.mjs` | Synchronous app mount, toolbar, canvas, observers, per-window teardown |
| `config.mjs` | App deployment configuration; relay disabled by default |
| `src/session.mjs` | One-worker lifetime, request/reply tracking, bounded shutdown |
| `src/engine-worker.js` | Loads raw Gecko artifacts, owns native runtime/pthreads, queues commands |
| `src/mailbox.mjs` | Pinned wasm32 ABI, serialization, frame copies, native status replies |
| `src/input.mjs` | Canvas-scoped mouse/key/wheel forwarding |
| `native/embed-host.cpp` | New native history/navigation/status API and ABI marker |
| `tools/patch_engine.py` | Exact-source patch with fail-closed anchors and patch hashes |
| `tools/fetch_engine.py`, `build_engine.sh`, `stage_engine.py` | Fetch/build/stage the real engine, not renderer stubs |
| `demo/` | Minimal independent test harness; not the target desktop |
| `fixtures/` | Real-engine manual test input; no fake screenshot/reference output |
| `tests/` | Offline adapter checks, explicitly using synthetic worker/memory peers |

The engine binaries are not supplied. The source package cannot display a real page before a compatible engine has been built and staged.

## 4. Why this uses the raw engine instead of the convenient upstream wrapper

The inspected wrapper's `destroy()` does not shut down its WASM runtime. Its optional GPU path references page-global canvases. Those are poor starting invariants for independently closable desktop windows.

Rather than adding global cleanup flags to preserve that wrapper, this implementation gives each window a dedicated owning Worker and uses the underlying software-framebuffer ABI. All engine lifecycle is contained there. A narrow native extension provides navigation and status; otherwise the adapter uses the existing raw mailbox.

This differs from upstream's usual main-thread wrapper embedding. `-sENVIRONMENT=web,worker` is present in the inspected build, but **that does not prove every custom import works when the runtime thread is a Worker**. Testing this deployment is the largest implementation gate. Inspect upstream `audio-out.js`, `webcodecs-bridge.js`, `gl-present.js`, `provider-fs.js`, `wasm-host-bridge.js`, coarse-clock callbacks and generated pthread bootstrap. A DOM-only import may still fail even with GPU/audio paths not intentionally used.

If you find such a failure, correct the relevant runtime boundary or explicitly narrow support. Do not reintroduce guest rendering into the host document or add a parallel fallback renderer. Do not call this complete because the toolbar opens.

## 5. Source and build gate

Wrapper pin: `bc69aaa5e2c5388bcf93a43b975b490bb940f4c0`.

Inner Gecko fork pin: `2e1e835a5da5907e5ceef19aade58a7493f1e34d`.

The native patch adds mailbox op **10** (control/status), C ABI marker **1**, and exports `PThread` for teardown. It removes the inherited page-global offscreen-canvas transfer selector. It preserves the original struct layout; native `static_assert`s and JS constants must agree.

Only raw `gecko.js/wasm/gecko.js`, `gecko.wasm` and `gecko.data` are supported. **Do not substitute upstream `dist/gecko.js`.** That is a different wrapper/bundle with embedded resources, not this runtime protocol. `wisp-client.mjs` is separately bundled from upstream's lockfile.

Review the patch before compiling. It has not been compiled here. Check actual `nsIWebNavigation` signatures, C++ linkage, generated `_browser_embed_abi`, `_xul_cmd_ptr`, `PThread.terminateAllThreads`, HEAP views, `FS`, `ENV`, raw data preloading and `createGecko` factory behavior. The build uses a pinned inner checkout and a separate `.work/` folder; it refuses to overwrite modified adapter files. Upstream build tools still execute downloaded code and may use user caches. Never run with elevated privileges merely to make the build pass.

Do not silently advance either source pin. If you update it, inspect the ABI, regenerate the reviewed patch and record new source provenance. Static hashes detect mismatch, not source trust. Byte-for-byte reproducible builds are not claimed.

`tools/build_engine.sh` targets the non-release upstream object directory intentionally for the first validation. It does not enable LTO or claim performance optimization. Stage scripts create `engine/manifest.json`, record hashes/sizes, and leave `runtimeTested: false`. Successful staging is not successful execution.

## 6. Window lifecycle gate

The adapter returns before engine fetch or initialization. Close during any await must prevent later results from changing a closed window. Starting/resetting a new runtime increments a generation counter. The desktop owns DOM removal; the app owns its observers, input listeners, request timers, copied frames and engine worker.

One worker/running Gecko per open window is the current design. Workers do not share a live profile or variables. Caching may share downloads; it does not eliminate runtime allocations. Do not start one at application discovery/import time.

The worker requests `PThread.terminateAllThreads()`, closes its Wisp connections and exits. The parent hard-terminates after 250 ms without blocking `dispose`. **Confirm experimentally that nested pthreads and transport sockets are gone after normal close, blocked-native close and close during startup.** Worker termination alone is not accepted as proof of nested cleanup.

Preserve command serialization. There is exactly one native mailbox per engine. Completed native error `-1` is recoverable; a timeout, malformed response or uncertain in-flight cancellation marks that instance failed. Never send another command into an uncertain mailbox. A reset creates a new runtime, not a second concurrent consumer of the old one.

The worker does not paint before the first document exists. Input backlog is bounded; adjacent pointer moves/resizes can coalesce, but transitions must not be reordered across key or button events. Frames use one outstanding transferred buffer with acknowledgment. Hidden windows stop requesting frames but **do not stop all guest execution**. Map desktop-minimize semantics to visibility if the real lifecycle provides them; do not invent that API here.

## 7. Deployment and security gate

This build needs SharedArrayBuffer/pthreads and cross-origin isolation. `tools/serve.py` supplies headers only for its isolated loopback harness. Do not apply those headers to the entire desktop without checking every other app: existing third-party embeds, cross-origin assets, OAuth/popup flows and WASM workloads can be affected. If the current deployment cannot provide the required isolation, report the actual conflict. An iframe replacement is not an acceptable fix for this request.

The source uses same-origin app-owned Workers and raw trusted engine glue. A Worker is a lifetime/concurrency boundary, **not a complete security boundary from the origin's credentials**. Guest JavaScript is intended to run in SpiderMonkey with engine-managed origins, but custom runtime imports and any engine escape remain security-sensitive. `host` is never sent to the worker; no privileged session/file API is exposed to pages. This is necessary, not sufficient for public untrusted browsing.

The upstream minimal embedder disables e10s/Fission, Safe Browsing/tracking protections and script watchdogs, among other compatibility-oriented defaults. Review `docs/SECURITY.md` and upstream `embed-init.cpp`. A port of Gecko is not equivalent to Firefox's mature native multiprocess sandbox. Do not test with personal accounts or sensitive credentials.

Network is off by default. If your existing networking includes Wisp, inspect the exact version, endpoint and authentication. The existing v86 or peer-network connection is not automatically compatible. The app's Wisp client is separate from the desktop's networking manager; no host-specific adapter has been fabricated. An existing authorized transport can replace this narrow boundary after review; do not implement a second global network stack.

The relay must authenticate authorized clients and enforce destination policy server-side: private/loopback/link-local/metadata ranges, DNS rebinding, IPv6 equivalents, ports, quotas, concurrent streams and abuse controls. Address-bar scheme validation does not restrict page subresources, redirects, scripts or socket destinations. Cookies in guest Gecko are not the desktop's host cookies; relay authentication is a separate concern. Do not put reusable secrets into a guest URL or proxy query string.

Determine TLS/certificate behavior and telemetry before use. Never disable TLS checks to make a website work. No server-side browser or open public relay is included.

## 8. Features not to overstate

The code targets a real browser engine, but the port/adapter is incomplete. Test CSS, DOM, JavaScript and HTTP behavior against actual fixtures. Do not advertise arbitrary-site compatibility from a Blink or Hello World test.

Audio, GPU/WebGL content, DRM, extensions, camera/microphone, permission prompts, clipboard, real host uploads/downloads, IME, accessibility, printing, popups/new windows and persistent profiles are not provided or qualified here. The single HTML import grants the selected bytes to the guest filesystem and does not resolve a local project's sibling assets. A native guest file picker does not grant host filesystem access. Add host-file integration only using actual scoped desktop services and explicit user intent.

The temporary profile makes closing/resetting destructive to guest state. Keep that visible. Do not change to a shared persistent profile to save memory; it would change isolation and ownership semantics. Multiple saved profiles, if later required, need deliberate ownership and conflict rules.

“Stop” is serialized with ordinary engine commands. A page that blocks the native thread may require Reset, and Reset loses guest state. The host input code is a first implementation, not a complete text-input/accessibility solution.

## 9. Integrate in bounded steps

First review source and run offline checks. Build and stage the pinned engine without touching the desktop. Prove the isolated harness loads the home fixture, then the smoke HTML, then local navigation and input. Do not enable the relay yet.

Next prove two independently mounted windows, close/reset races and all-worker cleanup. Measure initialization, resident memory, CPU, number of workers and close behavior. The upstream 512 MiB initial memory and 20-worker pool make arbitrary numbers of windows an unsafe default assumption.

Only then add the app to the real registry using its established mechanism. Preserve adjacent apps and services. Validate header/focus/resize interactions in the actual desktop. Finally configure the authorized relay and test approved external sites, destination restrictions, TLS and privacy.

Each gate in `docs/ACCEPTANCE.md` begins **NOT RUN**. Record commands, source revisions, browser/version, observations and failures. Mark passed only with evidence; retain failed fixtures rather than weakening them. A passing fake-worker unit test is not a passing Gecko teardown test.

## 10. Expected completion report

Return a concise report stating what changed, which upstream source/build was actually used, what real-browser tests ran, what remains blocked, and whether network access is enabled. Attach logs/artifacts and measured resource use. Do not label the app integrated merely because a loader imported `index.mjs`.

The user's goal is a browser engine running on the client, alongside existing apps, without making websites into desktop plugins. Preserve that goal while correcting this best-effort code wherever the real system or actual engine behavior shows it is wrong.
