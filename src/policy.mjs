export const ENGINE_ABI = 'browser-gecko-mailbox-v2';
export const UPSTREAM_COMMIT = 'bc69aaa5e2c5388bcf93a43b975b490bb940f4c0';
const enc = new TextEncoder();

export function normalizeNavigation(value) {
  if (typeof value !== 'string') throw new TypeError('URL must be text.');
  let s = value.trim();
  if (!s || /[\u0000-\u0020\u007f]/.test(s)) {
    throw new Error('Enter a URL without control characters or unescaped spaces.');
  }
  if (s === 'about:blank') return s;
  // A numeric host port is not a URI scheme. IPv6 literals also need https://.
  if (!/^[a-z][a-z\d+.-]*:/i.test(s) || /^[^/:]+:\d+(?:[/?#]|$)/.test(s) || s.startsWith('[')) {
    s = 'https://' + s;
  }
  let u;
  try { u = new URL(s); } catch { throw new Error('This is not a valid URL.'); }
  if (!['https:', 'http:'].includes(u.protocol)) {
    throw new Error('Address bar accepts http:, https:, and about:blank only.');
  }
  if (u.username || u.password) throw new Error('Credentials in URLs are not accepted.');
  if (enc.encode(u.href).length >= 8190) throw new Error('URL exceeds the engine mailbox limit.');
  return u.href;
}

export function relayURL(value, pageURL) {
  if (value == null || value === '') return null;
  const u = new URL(value, pageURL);
  if (!['ws:', 'wss:'].includes(u.protocol) || u.username || u.password || u.hash) {
    throw new Error('Configure a ws(s) relay without URL credentials or a fragment.');
  }
  if (new URL(pageURL).protocol === 'https:' && u.protocol !== 'wss:') {
    throw new Error('An HTTPS desktop requires a WSS relay.');
  }
  if (u.search || !u.pathname.endsWith('/')) {
    throw new Error('Relay must end in / and have no query. Use the existing service authentication, not URL tokens.');
  }
  return u.href;
}

export function boundedSize(width, height, maxWidth=1920, maxHeight=1080) {
  for (const n of [width, height, maxWidth, maxHeight]) {
    if (!Number.isFinite(n) || n < 1) throw new Error('Invalid viewport dimensions.');
  }
  const scale = Math.min(1, maxWidth / width, maxHeight / height);
  return {width: Math.max(1, Math.floor(width*scale)), height: Math.max(1, Math.floor(height*scale))};
}

export function trustedAssetURL(name, manifestURL) {
  if (typeof name !== 'string' || !/^[a-zA-Z0-9_.-]+$/.test(name) || name.startsWith('.')) {
    throw new Error('Engine asset must be a simple local filename.');
  }
  return new URL(name, manifestURL).href;
}

export function validateManifest(m, manifestURL, workerURL) {
  if (new URL(manifestURL).origin !== new URL(workerURL).origin) throw new Error('Engine assets must be same-origin.');
  if (!m || m.schema !== 1 || m.abi !== ENGINE_ABI || m.upstreamCommit !== UPSTREAM_COMMIT) {
    throw new Error('Unrecognized engine manifest, source revision, or ABI. Rebuild using this package.');
  }
  const names = ['runtime', 'wasm', 'data', 'wisp'];
  const out = {};
  for (const k of names) {
    const a = m.assets?.[k];
    if (!a || !Number.isSafeInteger(a.bytes) || a.bytes < 1 || !/^[a-f0-9]{64}$/.test(a.sha256)) {
      throw new Error(`Invalid ${k} asset descriptor.`);
    }
    out[k] = {...a, url: trustedAssetURL(a.file, manifestURL)};
  }
  if (out.runtime.file !== 'gecko.js' || out.wasm.file !== 'gecko.wasm' ||
      out.data.file !== 'gecko.data' || out.wisp.file !== 'wisp-client.mjs') {
    throw new Error('This adapter requires the raw engine artifacts, not the upstream UI bundle.');
  }
  return out;
}

export function textError(e) {
  return String(e?.message ?? e).slice(0, 4000);
}
