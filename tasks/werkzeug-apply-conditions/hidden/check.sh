#!/bin/bash
# Hidden check for werkzeug-apply-conditions. Runs in the working copy; this folder is tests_hidden/.
# The upstream tests for the two new Response methods, and the upstream test_wrappers.py / test_http.py at the fix commit
# (the same files minus the tests of the deprecated make_conditional helpers, so an agent may deprecate or keep them),
# replace the working copy's. The project's pytest config turns warnings into errors.
set -e
cp tests_hidden/test_apply_conditions.py tests_hidden/test_apply_range.py tests_hidden/test_wrappers.py tests_hidden/test_http.py tests/
exec uv run --no-project --python 3.13 --with-editable . --with pytest --with pytest-timeout --with cryptography \
  --with watchdog --with ephemeral-port-reserve --with greenlet --with pytest-xprocess \
  python -m pytest -p no:cacheprovider -q tests/test_apply_conditions.py tests/test_apply_range.py tests/test_wrappers.py tests/test_http.py
