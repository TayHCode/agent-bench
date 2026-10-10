#!/bin/sh
# Does a stranger's install work? Run from the repo root:  PY=python3.12 sh tests/install_check.sh
# 1. `pip install .` into a fresh venv, then `agentbench doctor` and `agentbench demo` (and python -m agentbench).
# 2. If uv is installed: `uvx --from . agentbench demo` (the same line a stranger runs, with a git URL instead of `.`).
# Everything lives in one disposable folder under $TMPBASE, $TMPDIR or /tmp (it must allow running scripts: nas-style
# noexec /tmp needs TMPBASE=/var/tmp) and is removed at the end. Needs network for pip's build tools.
PY=${PY:-python3}
ROOT=$(pwd)
D=$(mktemp -d "${TMPBASE:-${TMPDIR:-/tmp}}/agentbench-install.XXXXXX") || exit 1
fail() { echo "FAIL: $*"; cd "$ROOT" && rm -rf "$D"; exit 1; }
export UV_CACHE_DIR="$D/uv-cache" AGENTBENCH_HOME="$D/home" AGENTBENCH_CACHE="$D/cache"
echo "python: $($PY --version 2>&1)"
if $PY -m venv "$D/venv" > "$D/venv.log" 2>&1; then
  "$D/venv/bin/python" -m pip install -q "$ROOT" > "$D/pip.log" 2>&1 || { tail -n 5 "$D/pip.log"; fail "pip install failed"; }
elif command -v uv > /dev/null 2>&1; then  # no ensurepip here: uv makes the venv and installs the same package
  echo "(python venv unavailable; using uv venv + uv pip install)"
  rm -rf "$D/venv"; uv venv -q --python "$PY" "$D/venv" && uv pip install -q --python "$D/venv/bin/python" "$ROOT" > "$D/pip.log" 2>&1 || { tail -n 5 "$D/pip.log"; fail "uv install failed"; }
else
  tail -n 3 "$D/venv.log"; fail "venv unavailable (install your platform's python venv package, or uv)"
fi
mkdir "$D/work" && cd "$D/work" || fail mkdir
echo "== agentbench --help"; "$D/venv/bin/agentbench" --help | head -n 1 || fail help
echo "== agentbench doctor"; "$D/venv/bin/agentbench" doctor; echo "(doctor exit $?)"
echo "== agentbench demo"; "$D/venv/bin/agentbench" demo > "$D/demo.txt" 2>&1 || { cat "$D/demo.txt"; fail demo; }
grep -E 'stub-(solver|lazy)' "$D/demo.txt"; [ -s results.html ] || fail "no results.html"; echo "results.html: $(wc -c < results.html | tr -d ' ') bytes"
echo "== python -m agentbench"; "$D/venv/bin/python" -m agentbench --help | head -n 1 || fail "python -m"
"$D/venv/bin/python" -c "import agentbench, pathlib; assert (pathlib.Path(agentbench.__file__).parent / 'prices.toml').exists()" || fail "prices.toml not packaged"
if command -v uvx > /dev/null 2>&1; then
  echo "== uvx --from . agentbench demo"
  rm -f results.html
  uvx --from "$ROOT" agentbench demo > "$D/uvx.txt" 2>&1 || { tail -n 15 "$D/uvx.txt"; fail "uvx demo"; }
  grep -E 'stub-(solver|lazy)' "$D/uvx.txt"; [ -s results.html ] || fail "uvx: no results.html"
else
  echo "uvx not installed: SKIPPED"
fi
cd "$ROOT" && rm -rf "$D"
[ ! -e "$D" ] && echo "removed $(basename "$D"); ALL OK"
