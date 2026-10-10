Bug report for `humanize`:

    >>> import humanize
    >>> humanize.intcomma(10**400 + 123)
    OverflowError: int too large to convert to float

Python integers have no size limit, so `intcomma` should format them with thousands
separators however large they are (the result for `10**400 + 123` is `10`, then `,000`
132 times, then `,123`). Negative values should work too. Small values, floats, strings and
the `ndigits` argument must behave exactly as before.

Please fix it in `src/humanize/` and add a regression test to `tests/test_number.py`.

Run the number tests with:
`PYTHONPATH=src uv run --no-project --with pytest --with freezegun --with pytest-benchmark python -m pytest tests/test_number.py -q`
(`src/humanize/_version.py` is a stub added for this checkout, leave it alone.)
