#!/bin/bash
set -eu
cp tests_hidden/test_fields.py tests/test_fields.py
cp tests_hidden/test_main.py tests/test_main.py
cp tests_hidden/test_parse.py tests/test_parse.py
cp tests_hidden/test_private_attributes.py tests/test_private_attributes.py
exec .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_fields.py tests/test_main.py tests/test_parse.py tests/test_private_attributes.py
