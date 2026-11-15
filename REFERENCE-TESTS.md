# Owned original reference tests

These2 original test files belong to browser because their imported source modules match this repository’s exact captured blobs. Current implementation files and assertions are unchanged. Import and proven fixture/resource URL locators are ported to this repository; no cross-repository private source imports or compatibility path shims are added.

Mechanical source-test baseline `5b92ef1898b414eb3f2747eff1d4b1ddf73f8870`; merge `753f119d7e48e4e264570e703bee12737166cd27`. Private phase44 preserves earlier paths, explicit copy boundaries and source-to-result commit/ref maps. The locator-normalized complete AST is unchanged, not just selected assertions.

Run `npm run test:reference`. This is Node unit/reference qualification of the retained domain modules, not browser/worker/kernel/renderer/storage/authentication/human-agent acceptance. Current app hosting/build and shared-operation integration gates remain separately open.

Captured baseline and current port: 9 pass, 0 fail, 0 cancelled, 0 skipped across 9 reported Node subtests. Top-level assertion-only files count as one reported Node subtest, not individual assertions.

Initial controlled baseline fixture gaps were closed using existing exact original tracked demo/resource bytes: no test changed to bypass them. Current tests read the corresponding owned files through verified URL locators.
