// Map the engine's top-level network result to conservative user-facing text.
// An aborted request is intentionally silent: redirects can abort a request as
// part of normal navigation. The Stop button supplies its own acknowledgement.
const ABORTED=0x804b0002;
export function navigationFeedback(progress) {
  if (!progress || !Number.isSafeInteger(progress.sequence) || progress.sequence<0 ||
      !Number.isInteger(progress.state) || progress.state<0 || progress.state>2 ||
      !Number.isInteger(progress.result) || progress.result<0 || progress.result>0xffffffff ||
      !Number.isInteger(progress.httpStatus) || progress.httpStatus<0 || progress.httpStatus>999) {
    throw new Error('Malformed native navigation progress.');
  }
  if (progress.state===1) return 'Loading…';
  if (progress.state!==2 || progress.result===ABORTED) return null;
  if (progress.result!==0) return 'Could not load the page. Check the address or connection.';
  if (progress.httpStatus>=400 && progress.httpStatus<=599) return `The site returned HTTP ${progress.httpStatus}.`;
  return 'Page loaded.';
}
