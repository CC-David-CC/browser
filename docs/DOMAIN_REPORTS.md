# Requested domain-usage reports

The feature is enabled on the live Simplified Browser service. The Browser
records domain names and timestamps in account-scoped storage on
the current device. It does not record page paths or page contents. Existing
browser data can be cleared by the device owner. No report is sent unless a
configured administrator creates a time-limited request while the Browser is
open. A browser with data sends one snapshot for that request and keeps a
local receipt to avoid repeated submissions. Other devices respond separately.

An authorized administrator can use Browser → Diagnostics → Domain usage
reports to request a report for one hour and view totals across responding
devices. Reports are held on the server until an administrator removes them;
the operator API also supports per-account totals and deleting a request and
its stored reports. Only configured registered administrator subjects can
create, list, summarize or remove requests. All signed-in accounts can see
active requests and submit only their own signed browser report.

Each event is signed by a device-held key and linked to the previous event.
The server verifies the chain, signature, origin and authenticated account
scope. A signature proves that this key signed the submitted data; it does not
prove a human identity, that timestamps are accurate, or that the device
reported every domain. Clearing browser storage can remove the history or key.

To enable the service, a root-owned administrator-subject list and a private
service-owned report database must be configured explicitly. The service
renderer's optional `--reports` mode uses `/etc/codi-browser/report-admins.json`
and `/var/lib/codi-browser-reports/reports.sqlite3`. Omit this option to keep
the endpoints and storage disabled. Site-wide server access auditing is a
separate setting and remains disabled by default.

On 2026-10-31, a live disposable account generated a real Browser request to
example.com. The test confirmed no report for that account was stored before
an operator-created request, then verified the submitted signed report and
its unchanged summary after a relay restart. The test request and account
were removed. The test created the request through the coordinator as its
service user, so it did not independently test an administrator's UI login.

A subsequent live desktop test exercised the administrator UI itself using a
registered disposable account. After the device recorded example.com locally,
the test used **Request reports for one hour** and **Show totals**, and saw
its signed device report in the UI. It removed that account's test requests
and reports, restored the exact pre-test administrator list, and removed the
account. The guarded test temporarily restarts the relay and is implemented in
`tests/browser-live-report-admin.test.mjs` and
`tests/live-browser-report-admin-guard.py`; the latter leaves a root-only
journal for explicit recovery if interrupted. The first attempt demonstrated
that systemd `active` can precede socket readiness and received a transient 502;
the guard now waits until the actual relay socket accepts a connection.

A later live recovery test did not create a report request: it stopped the
Browser relay before opening a disposable account's Browser window and saw an
unavailable message, then restarted it and reconnected with **Reset engine**.
It repeated the test with an already-open Browser and verified that a new page
loaded after reconnection. This verifies the manual recovery flow, not automatic
restoration of a temporary browsing profile. Server-side audit remained off.

The current live release was also tested with a disposable account while no
administrator report request was active. Its example.com event appeared in
browser storage; over more than one 30-second polling interval, the test saw
no report-submission request and no stored report for that account. No global
report request was created, and the test account was removed. This checks the
observed no-request path, not whether a device reports every domain or whether
other browsers are free of requests at other times.
