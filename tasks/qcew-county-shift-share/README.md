# Preparing the data task

The shipped folder is a reconstruction recipe, with no input archive or answer
CSV bundled. The public CLI invokes the checksum-pinned data preparer.
Prepare outside the source tree:

```sh
agentbench task prepare qcew-county-shift-share --tasks-dir /tmp/benchmark-tasks --cache-dir /tmp/benchmark-downloads
```

Then use `--tasks-dir /tmp/benchmark-tasks` with the existing verify/run commands.
The download is about 356 MB; the CSVs decompress to about 2.67 GB. SHA-256 pins
both source vintages. A later BLS revision is rejected, preserving cached files.
The preparer builds exact rational known answers outside `repo/`, copies them
to `gold/` and `hidden/`, and exposes only the raw inputs and their field contract.
No model, private data, API key, external write or paid service is involved.

An independent full-table SQL cross-check is available in
`tests/qcew_reference_crosscheck.py` (DuckDB). It reads the original archives
and compares every answer cell; arguments are documented in its docstring.

See [ACCEPTANCE.md](ACCEPTANCE.md) for the fresh prepare, repeated checks and
single valid Sonnet probe (failed full keysets; hard candidate, n=1).
