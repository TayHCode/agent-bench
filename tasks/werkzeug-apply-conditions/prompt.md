This is an issue from the Werkzeug tracker; please implement what it asks for.

**`make_conditional` has a lot of problems**

It handles both evaluating preconditions and applying ranges. It does not match the order and logic in RFC 9110
sections 13 and 14. It looks like some of this confusion was due to trying to add range handling into the existing
conditional handling method, making the API a lot more complicated.

Some of the problems, and problems revealed in other parts of the code:

- Only applies to `GET` and `HEAD`, but conditional responses should apply to mutating methods as well.
- Processes range requests first, then conditional requests. This is backwards.
- Does not ensure the ETag being compared is strong/weak depending on what's being checked.
- `is_resource_modified` returns a bool, which is insufficient for the checks described in the spec. It needs to
  distinguish between 200, 304, 412, and 416. `make_conditional` tries to guess what status code to apply based on what
  `is_resource_modified` returns and what headers are set.
- Does not validate directly that the requested range unit is `bytes`. Allows setting `Accept-Ranges` to something
  besides `bytes` even though it will only handle bytes.
- Precedence of `If-Match`, `If-Modified-Since`, `If-None-Match`, and `If-Unmodified-Since` is messed up.
- `is_resource_modified` doesn't take `if_unmodified_since`, so that header is completely ignored.
- `If-Range` date uses `<=` comparison instead of `==`.
- Sets the `Date` header for some reason. The spec does not mention this.
- Similarly, sets `Content-Length`, but `to_wsgi_headers` already does that.
- Doesn't raise on 412, only sets the status code. So 412 still contains the original response's body and headers.
  `to_wsgi_response` doesn't handle clearing this like it does for 304.
- Invalid ranges produced 416, but that's only for valid but unsatisfiable ranges. Should return 200 for those.
- Considered multiple ranges invalid (and incorrectly returned 416). Spec says can either choose to ignore and return 200,
  or use first range only.
- Suffix range larger than the complete length was considered invalid instead of clamped.
- `ETagSet.contains/_weak` assume the given value had the correct weak/strong marker. Now that `ETag` exists, that can be
  passed and checked directly.
- `SharedDataMiddleware` tries to handle this again on its own, but only 304, doesn't support 412, 416, or ranges at all.
  Can use `send_file` instead.

This can be split into two new methods on `Response`, `apply_conditions(request)` and `apply_range(request)`.
`make_conditional`, related helper methods, and `is_resource_modified`, can be deprecated.

*Maintainer follow-up:* after 412 handling was initially added, people reported that 412 responses didn't have a body.
The "fix" for that stopped removing the body for 412 in `get_app_iter`. However, `make_conditional` didn't clear the
original body. What should have happened is it should have raised instead of setting the status on the existing
response. That will be fixed now, so 412 will have a body (the error message) but a failed condition will not send the
original body.

**Interface to implement** (`src/werkzeug/wrappers/response.py`, and whatever helpers you need elsewhere):

- `Response.apply_conditions(request, *, exists=True)`: evaluate the request's preconditions against the response's
  `ETag` and `Last-Modified`; `exists` says whether the target resource exists (for `*` conditions). It raises the
  matching werkzeug HTTP exception when a precondition fails and sets the status to 304 when the response is not
  modified.
- `Response.apply_range(request)`: apply a `Range` request, with `If-Range`, to the response; it raises
  `RequestedRangeNotSatisfiable` for a valid but unsatisfiable range. It works from the response's `Content-Length`
  header: a response without one (or with 0) is left alone.

Please add tests, `tests/test_apply_conditions.py` and `tests/test_apply_range.py`. Run the suite with
`uv run --no-project --python 3.13 --with-editable . --with pytest --with pytest-timeout --with cryptography --with watchdog --with ephemeral-port-reserve --with greenlet --with pytest-xprocess python -m pytest tests/test_http.py tests/test_wrappers.py` (warnings are errors in this project).
