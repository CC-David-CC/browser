#!/usr/bin/env bash
# Deliberate, heavyweight build on the integrator's development Linux machine.
# NOT run by mount(), the desktop, or a visiting user's browser.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${1:-$ROOT/.work/firefox-wasm}"
if [[ ! -d "$SRC/.git" ]]; then
  printf '%s\n' 'Source not fetched. Review README/docs/AGENT_HANDOFF, then run:' "python3 '$ROOT/tools/fetch_engine.py' --into '$SRC'" >&2; exit 1
fi
SRC="$(cd -- "$SRC" && pwd)"
for cmd in git make python3 node pnpm rustc cargo zstd cmake ninja pkg-config; do
  command -v "$cmd" >/dev/null || { echo "Missing prerequisite: $cmd. No packages were installed." >&2; exit 1; }
done
# This checks the pin and refuses to overwrite unrelated modifications.
python3 "$ROOT/tools/patch_engine.py" "$SRC"
printf '%s\n' 'Building real Gecko. Read upstream requirements for Linux libraries, Rust and Emscripten.'
# Keep toolchain/bootstrap writes inside the dedicated work directory where supported.
# Upstream tools may also populate normal Rust/pnpm caches. They do not touch desktop apps.
export MOZBUILD_STATE_PATH="$SRC/.mozbuild"
# Never patch an inherited/system-wide SDK or use a foreign mozconfig.
export EMSDK="$SRC/emsdk"
export EM_CONFIG="$SRC/em_config"
export MOZCONFIG="$SRC/mozconfig.full.emscripten"
# make build bootstraps this directory before invoking mach, which resolves
# the target compiler by name from PATH.
export PATH="$EMSDK/upstream/emscripten:$PATH"
cd "$SRC"
pnpm install --frozen-lockfile
# upstream make bootstraps its pinned Gecko fork + patched Emscripten 6.0.1.
make firefox
EXPECTED_GECKO="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["gecko_commit"])' "$ROOT/upstream.lock.json")"
ACTUAL_GECKO="$(git -C "$SRC/firefox" rev-parse HEAD)"
[[ "$ACTUAL_GECKO" == "$EXPECTED_GECKO" ]] || { echo 'Wrong inner Gecko checkout; refusing build.' >&2; exit 1; }
[[ -z "$(git -C "$SRC/firefox" status --porcelain)" ]] || { echo 'Inner Gecko checkout contains changes; review separately.' >&2; exit 1; }
make build RELEASE= LTO=
# Build RAW MODULARIZE engine artifacts. Do not use dist/gecko.js (UI wrapper).
GECKO_RELEASE= bash gecko.js/build-lib.sh
node "$ROOT/tools/bundle_wisp.cjs" "$SRC" "$ROOT/engine"
python3 "$ROOT/tools/stage_engine.py" "$SRC"
printf '%s\n' 'Build staged. Next: real browser smoke tests in docs/ACCEPTANCE.md. Not approved for deployment.'
