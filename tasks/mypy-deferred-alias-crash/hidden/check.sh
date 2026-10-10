#!/bin/bash
# Hidden check for mypy-deferred-alias-crash. Runs in the working copy; this folder is tests_hidden/.
# The upstream check-python312.test and check-typevar-tuple.test at the fix commit replace the working copy's (they hold
# the two new regression cases); then the suites for type aliases, tuples, type variable tuples and Python 3.12 syntax run.
set -e
cp tests_hidden/check-python312.test test-data/unit/check-python312.test
cp tests_hidden/check-typevar-tuple.test test-data/unit/check-typevar-tuple.test
exec uv run --no-project --python 3.13 --with-editable . --with attrs --with filelock --with lxml --with psutil \
  --with pytest --with pytest-xdist --with setuptools --with tomli --with typing_extensions --with mypy_extensions \
  --with pathspec --with librt --with "ast-serialize>=0.12.1,<1.0" python -m pytest -p no:cacheprovider -q -n 0 \
  mypy/test/testcheck.py -k "check-python312 or check-typevar-tuple or check-type-aliases or check-tuples or check-recursive-types or check-newsemanal or check-typeddict"
