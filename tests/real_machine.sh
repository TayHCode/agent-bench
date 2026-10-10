#!/bin/sh
# Real-machine check with a stub contestant (no model, no cost). Run from the root of an unpacked copy of the repo:
#   PY=python3.12 sh tests/real_machine.sh
# Everything lives in one disposable folder, agentbench-b1-<stamp>, under $TMPBASE, $TMPDIR or /tmp (it must allow running
# scripts: some machines mount /tmp noexec, then set TMPBASE); it is removed at the end and the
# removal is checked. Needs python >= 3.11 and git. Touches nothing outside that folder; no network.
set -eu
PY=${PY:-python3}
ROOT=$(pwd)
STAMP=$(date +%Y%m%d%H%M%S)
D=${TMPBASE:-${TMPDIR:-/tmp}}/agentbench-b1-$STAMP
D=$(printf %s "$D" | sed 's|//|/|g')
mkdir -p "$D"
fail() { echo "FAIL: $*"; rm -rf "$D"; exit 1; }
export AGENTBENCH_HOME="$D/home" AGENTBENCH_CACHE="$D/cache" PYTHONPATH="$ROOT/src"
AB="$PY -m agentbench.cli"
echo "python: $($PY --version 2>&1); git: $(git --version)"

SHA=$($PY tests/toyrepo.py "$D/toy")
echo "== from-commit"
$AB task from-commit "$D/toy" "$SHA" --id toy-null-total --check "python3 -m unittest discover -s tests" | tail -n 4 || fail from-commit
[ -f "$AGENTBENCH_HOME/tasks/toy-null-total/hidden/overlay/tests/test_cart.py" ] || fail "no hidden overlay"
grep -q 'prices or' "$AGENTBENCH_HOME/tasks/toy-null-total/gold/cart.py" || fail "gold lacks the fix"
! grep -q 'prices or' "$AGENTBENCH_HOME/tasks/toy-null-total/repo/cart.py" || fail "the fix leaked into repo/"
echo "Fix total(None) so it returns 0." > "$AGENTBENCH_HOME/tasks/toy-null-total/prompt.md"

cp tests/stub_claude.py "$D/claude-stub"
chmod +x "$D/claude-stub"
printf '{"fix_dir": "%s"}' "$AGENTBENCH_HOME/tasks/toy-null-total/gold" > "$D/claude-stub.json"
(cd "$D" && ./claude-stub < /dev/null > /dev/null 2>&1) || fail "cannot run a script from $(dirname "$D") (noexec mount?): set TMPBASE to a folder that allows it"
export AGENTBENCH_CLAUDE_BIN="$D/claude-stub"

echo "== plan"
$AB plan --ledger-cap 1 | sed -n 1,3p
echo "== matrix with the stub contestant (2 runs)"
$AB matrix --ledger-cap 1 > "$D/matrix.txt" || { cat "$D/matrix.txt"; fail matrix; }
grep -c 'passed=True' "$D/matrix.txt" | grep -qx 2 || { cat "$D/matrix.txt"; fail "expected 2 passing stub runs"; }
grep 'passed=' "$D/matrix.txt" | sed 's|^\(.*\)$|  \1|'
$AB report --runs "$AGENTBENCH_HOME/runs" --html "$D/results.html" > /dev/null || fail report
[ -s "$D/results.html" ] || fail "empty report"
echo "report: ok ($(wc -c < "$D/results.html" | tr -d ' ') bytes)"

echo "== no network (unshare -rn)"
if command -v unshare > /dev/null 2>&1 && unshare -rn $PY -c "import socket,sys
try: socket.create_connection(('1.1.1.1', 53), timeout=2)
except OSError: sys.exit(0)
sys.exit(9)" > /dev/null 2>&1; then
  unshare -rn $AB run --task toy-null-total --contestant haiku-5-5@claude-code --out "$D/nonet-runs" | tail -n 1 | grep -q 'passed=True' || fail "stub run failed with the network off"
  echo "stub contestant completed with the network off: ok"
else
  echo "unshare -rn not available or not permitted here: SKIPPED"
fi

echo "== full unit-test suite"
TMPDIR=$(dirname "$D") $PY -m unittest discover -s tests > "$D/unit.txt" 2>&1 || { tail -n 40 "$D/unit.txt"; fail "unit tests failed"; }
tail -n 3 "$D/unit.txt"

rm -rf "$D"
[ ! -e "$D" ] || { echo "FAIL: cleanup left $D"; exit 1; }
echo "cleanup verified: $(basename "$D") removed"
echo "ALL OK"
