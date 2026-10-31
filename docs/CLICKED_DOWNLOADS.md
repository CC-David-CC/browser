# Clicked downloads

Browser runs each clicked download inside its ephemeral Gecko
profile, using that profile's cookies and the authenticated relay. A completed
download appears in the Browser window. It is copied to the account's My files
only when the user chooses **Save to My files** and a name. The normal browser
mirror then synchronizes it to the server; an interrupted sync may need to
finish later. Discard removes the temporary copy. Resetting or closing the
window warns if downloads are still pending. Browser reload/close warnings are
subject to the outer browser's own behavior.

Each window has a separate queue and a limit of three active or waiting files,
up to 128 MiB each. Oversized and interrupted transfers report an error. These
limits do not bound all Gecko or web-page memory, and network buffering can
make a rejected stream slightly exceed the nominal transfer threshold.
Temporary downloads disappear on reset, close, or crash; the warning cannot
recover unsaved downloads from a crash. The separate Download URL feature
does not use Gecko cookies. This is not a general host-file or upload bridge.

## Source and maintenance

`engine-support/SOURCES.json` identifies each Mozilla source file, its exact
Gecko revision, original and packaged SHA-256 hashes, and modified status.
The files are distributed under their Mozilla Public License 2.0 headers.
The modified `HelperAppDlg.sys.mjs` sends downloads to isolated temporary job
directories and publishes start/failure markers. The modified
`DownloadLegacy.sys.mjs` publishes completion and enforces streaming size
limits. The worker verifies all module sizes and hashes before installing them
into the temporary runtime. Update the metadata, resource pins, tests, and
public corresponding-source distribution together when changing these files.

## Verification

Unit tests cover resource pins, malformed paths, limits, and download lifecycle:
`node --test apps/system/browser/tests/*.test.mjs tests/browser-guest-downloads.test.mjs tests/browser-download-resources.test.mjs`.
The isolated integration fixture in `tests/browser-download-http-fixture.py`
and `tests/browser-download-preview.py` is test-only: its relay deliberately
maps a synthetic public hostname to loopback. Never deploy that override.
`tests/browser-clicked-downloads.test.mjs`,
`tests/browser-download-windows.test.mjs`, and
`tests/browser-download-stream-limit.test.mjs` exercise real Gecko transfers,
cookie-protected delayed files, explicit save, account synchronization,
failure/size limits, and independent window cleanup. Phone-sized automated
tests emulate touch; they do not substitute for a physical phone test.
