#!/bin/bash
set -eu
cp tests_hidden/check-python312.test test-data/unit/check-python312.test
exec uv run --no-project --python 3.13 --with-editable . --with attrs --with filelock --with lxml --with psutil --with pytest --with pytest-xdist --with setuptools --with tomli --with typing_extensions --with mypy_extensions --with pathspec --with librt --with "ast-serialize>=0.12.1,<1.0" python -m pytest -p no:cacheprovider -q -n 0 mypy/test/testcheck.py -k "check-python312 or check-typevar-tuple or check-generics or check-parameter-specification or check-callable or check-overloading or check-typeddict"
