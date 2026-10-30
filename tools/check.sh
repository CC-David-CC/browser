#!/usr/bin/env bash
# Offline source checks. Does not fetch, build, or run Gecko or open a browser.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
for file in index.mjs config.mjs src/*.mjs src/*.js demo/*.mjs tools/*.cjs tests/*.mjs; do node --check "$file"; done
for file in tools/*.sh; do bash -n "$file"; done
python3 - <<'PY'
from pathlib import Path
for root in ('tools','tests'):
    for p in Path(root).glob('*.py'):compile(p.read_text(),str(p),'exec')
PY
node --test tests/*.test.mjs
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py' -v
printf '\nOffline checks complete. Gecko and desktop/browser integration remain UNTESTED.\n'
