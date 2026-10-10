Our worker profile shows a lot of CPU spent building log strings that are never emitted:
the package logs with f-strings (`logger.debug(f"... {message}")`), so Python formats
every message eagerly, even when the level is disabled.

Please clean this up across the `taskiq/` package:

- Pass log arguments lazily (`logger.debug("... %s", message)`) everywhere the package
  logs. Keep every message's wording; only change how the values are passed.
- Turn on ruff's flake8-logging-format rules (`"G"`) in the ruff `lint.select` list in
  `pyproject.toml` and fix everything it then reports in `taskiq/`.
- Do not change behaviour or the tests.

Check with `uvx ruff check --select G taskiq`. Install the development/test dependencies listed in the upstream `pyproject.toml`, then run `python -m pytest tests --ignore tests/opentelemetry -q -n 0`.
