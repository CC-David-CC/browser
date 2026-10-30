# Browser (experimental)

This app is intended to run an independent Gecko/SpiderMonkey engine in the
visitor's browser, painting into its own desktop window. Pages do not receive
CodiServer app services. Each window owns its engine worker and temporary
profile; closing or resetting it discards that profile.

**Status:** adapter source only. The pinned Gecko engine has not yet been built
or tested, and this app is not registered in the desktop menu. Public website
access also needs an authenticated, policy-controlled Wisp relay; none is
configured. It is not ready for sensitive browsing or untrusted users.

The regular app builder packages the entry and worker support declared in
`app.json`. A usable build also needs the actual engine assets and corresponding
manifest packaged and tested; the generated engine assets are not stored in Git.
Build inputs and exact revisions are in `upstream.lock.json`, `native/` and
`tools/`. Development-only tests, harness and fixtures are in `tests/`, `demo/`
and `fixtures/`.

Read `docs/AGENT_HANDOFF.md` and `docs/SECURITY.md` before integrating or enabling
networking. The upstream engine differs from a fully sandboxed native Firefox.
The original adapter is MIT licensed; see `docs/LICENSE` and
`docs/THIRD_PARTY_NOTICES.md` for distribution requirements. The supplied
`docs/SOURCE_MANIFEST.json` describes the original handoff, before this folder
was reorganized; it is not a manifest of the current files.
