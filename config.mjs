// Deployment values owned by THIS app, not new host APIs.
// No public relay, remote browser, or automatic external page is configured.
export const config = Object.freeze({
  manifestURL: new URL('./engine/manifest.json', import.meta.url).href,
  wispURL: null,                 // Integrator: reviewed ws(s) endpoint ending in '/'.
  width: 960,
  height: 640,
  maxWidth: 1920,
  maxHeight: 1080,
  framesPerSecond: 20,
  startupTimeoutMs: 120000,
  commandTimeoutMs: 45000,
  maxHTMLBytes: 2 * 1024 * 1024,
});
