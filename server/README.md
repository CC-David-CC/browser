# Browser backend source

`browser_service/` owns Browser relay admission, short-lived leases, HTTP routes and audit-switch transactions. The existing `relay/` package owns Wisp, policy, downloads and reports. These are source modules; installing this package starts no listener and changes no service.

The mechanical extraction preserves six backend files and four focused test files, with original blobs and modes verified before the integration commit. Authorization now imports the public `webos_accounts.jose` primitives. Focused tests use this repository's layout. No legacy checkout or private cross-repository source import is required.

The retained `browser_service/requirements.lock` is historical deployment evidence, not the new assembly dependency authority. The installable Python package declares its direct dependencies in `pyproject.toml`; a future release must include these in its reviewed complete dependency lock. Do not install the historical lock over the assembly environment.

The issuer's Browser-purpose grant endpoint, launcher composition, trusted ingress, lifecycle cleanup, real Gecko assets and human/agent integration still require qualification. The backend is not enabled in the current desktop or test deployment. Mixed system/operator tests remain in private recovery pending their owners. Never invoke service-changing legacy operators as tests.

## Checks

After installing the reviewed Accounts package and this package into an isolated environment:

```sh
python -m unittest discover -s tests -p 'test_*.py'
python tests/legacy-browser-service/browser-audit-switch-test.py
python tests/legacy-browser-service/browser-audit-http-test.py
python tests/legacy-browser-service/browser-report-http-test.py
python tests/legacy-browser-service/browser-sources-auth-test.py
```

Qualification: 56 Python tests pass (42 existing relay tests, six signed authorization protocol tests, eight unchanged focused backend tests). Signed tests use generated fixture issuer/client keys; they do not prove issuer HTTP endpoint integration. The JavaScript suite retains its pre-existing result: 93 pass and one host-contract failure. No assertion was weakened. Installed-wheel imports and the packaged policy asset were separately checked with Browser source, original workspace and private source recovery hidden.
