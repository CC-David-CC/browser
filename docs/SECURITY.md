# Security review required before public or sensitive use

**Status: not security-reviewed, not browser-tested, not production-approved.** No claim of a hardened sandbox is made by this package.

## Intended boundaries

Ordinary page JavaScript executes in the guest SpiderMonkey runtime, not by evaluating page scripts in the outer browser. The guest HTML/CSS/DOM live in Gecko; only copied framebuffer bytes and selected native navigation status cross into the desktop UI. No guest page is supposed to receive the desktop `host`, its session object, or a file-service callback.

The engine runs in a same-origin Worker for lifecycle ownership. WebAssembly linear memory, an independent JS interpreter, a Worker, a ShadowRoot and a native browser security model are different things. None individually proves a secure public browsing service. Trusted runtime glue executes as JavaScript with the Worker's origin authority. An unsafe custom import, engine vulnerability, dependency compromise or integration mistake may breach the intended boundary.

This package does not expose a page-to-host generic RPC channel or a host `eval` operation. Its mailbox driver rejects guest evaluation and DOM-mirroring opcodes. That narrows the intended interface; it does not formally prove isolation.

## Upstream settings that need explicit review

The inspected minimal embedder in `gecko.js/src/embed-init.cpp` intentionally changes production Firefox defaults. In particular:

- e10s/Fission and subprocess paths are disabled for this port. Do not equate this with native Firefox's multiprocess security architecture.
- Safe Browsing and tracking-protection preferences are disabled in the inspected initialization path.
- Slow-script watchdog limits are disabled. A page can hang the guest main thread; the host must be able to terminate the owning runtime.
- Top-level `data:` navigation restrictions are relaxed, and media/background-playback defaults are modified. The adapter's address bar rejects data URLs, but page-originated navigations are not the same entrypoint.
- There is additional chrome-mode configuration. This adapter does not enable `GECKO_CHROME`, provide an extensions manager or validate those paths.

Do not silently restore or weaken preferences merely to make one fixture pass. Determine why a preference was changed, which code path is actually active, and whether restoring the protection works in this port. Record the resulting supported configuration.

The upstream JS-to-WASM JIT is marked experimental and is disabled here. Do not enable it without separate correctness/security qualification.

## Networking and relay authority

`wispURL: null` leaves the guest socket bridge without a relay. The upstream transport explicitly checks for an injected URL and client before opening a connection. This adapter does not include a public fallback relay. Asset fetches still happen when the app starts: offline-page operation is not a claim that the initial engine download needs no network.

Once Wisp is configured, guest websites can initiate requests through that relay. The relay reaches networks from **its own location**, not the user's physical network. It is therefore a potential SSRF/abuse boundary. Validate resolved destinations and ports on the relay, including IPv4/IPv6 private, loopback, link-local and cloud-metadata ranges, DNS rebinding and redirects. Any authorized intranet access must be an explicit policy choice, not an accidental default.

Authenticate relay clients; enforce rate/connection/bandwidth quotas and per-user authorization. Origin checking by itself is not comprehensive authentication for a publicly reachable service. Avoid reusable URL tokens. A query-free endpoint does not implement authentication by magic: the integrator must review the actual service mechanism.

Do not assume the outer site's CSP evaluates the inner guest's website requests. The outer browser sees the relay WebSocket, while guest requests are inside that transport. Likewise, address-bar `http/https` validation is not a destination firewall for subresources or programmatic requests.

Audit TLS and trust-store behavior with controlled positive/negative tests. Do not disable certificate validation. Preserve endpoint identity and do not inject user content into browser chrome. Network, destination and timing metadata can be visible to the relay; HTTP content is not encrypted by HTTPS merely because the outer relay uses WSS. Do not promise confidentiality beyond the actual protocol path.

## Files, cookies and profiles

The engine is configured with an ephemeral in-memory profile and no host-file provider. Native browser cookies and guest page storage are not intended to be the desktop's cookies/storage. Reset/close loses guest state.

The Open HTML action copies a specifically selected file into the guest virtual filesystem. Other files inside that runtime, including previous imports and engine resources, are not proven to have per-page isolation. Treat placing a file into a guest as a grant to that runtime, not a capability securely scoped to one displayed document.

There is no host clipboard bridge, background upload integration, desktop download destination or persistent profile directory. Do not add broad `host.files` authority to solve a single file transfer. Use explicit selection and the real desktop's permission model.

## Availability and resource use

The raw engine declares substantial initial memory and a pthread pool. Additional content can consume more. Input queues and frame buffers are bounded by the adapter; the engine's native allocations, guest scripts and network activity are not thereby fully bounded. A disabled/hidden canvas does not suspend the entire runtime.

Close and Reset must terminate runtime descendants, not only remove DOM elements. Confirm this under normal operation, loading, blocked scripts, heavy allocation and network failure. Worker unit tests use a fake peer and cannot establish actual pthread termination or RSS/GPU-resource release.

The canvas-only output also creates accessibility and input limitations. Do not claim an accessible consumer browser until you have a real accessibility/text-input strategy and tests.

## Origin/header/dependency review

SharedArrayBuffer requires an appropriate cross-origin-isolated deployment. COOP/COEP changes may affect every other desktop app. The local development server is not production middleware and does not authorize broad changes to the desktop origin.

Generated artifacts are pinned to source revisions and checked with hashes. An attacker who can replace both manifest and binaries can replace the runtime; hashes are integrity checks, not a signing chain or security audit. Build dependencies execute on the developer machine. Use an unprivileged, dedicated build workspace and review upstream build actions before running them.

Before distribution, review third-party licenses and source obligations. Before exposing untrusted public browsing, complete a threat model for engine imports, origin credentials, relay access and profile ownership. Passing an “outer sentinel not visible” fixture is only a smoke observation, not proof of exploit resistance.
