mypy crashes with an INTERNAL ERROR on the file below. Please find the root cause and fix it in `mypy/`,
and add regression cases to `test-data/unit/` (for example in `check-python312.test` or `check-typevar-tuple.test`).

**Crash report** (from a user; mypy 1.20.2, also reproduces on the latest release and on this checkout)

mypy is crashing when processing the type definition of a tuple that unpacks another tuple. Command:
`python -m mypy --python-version 3.12 --no-incremental --cache-dir=/dev/null --show-traceback mre.py`

```python
"""
Minimal reproducer: mypy crashes on a nested tuple type alias unpack.
"""

from collections import deque

type Inner = tuple[int, str]
type Outer = tuple[bool, *Inner]


class K(Base):
    q: deque[Outer] = deque()


class Base: ...
```

Traceback:

```
mre.py:12: error: INTERNAL ERROR -- Please try using mypy master on GitHub:
https://mypy.readthedocs.io/en/stable/common_issues.html#using-a-development-mypy-build
Please report a bug at https://github.com/python/mypy/issues
version: 1.20.2
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "mypy/checkexpr.py", line 6092, in accept
  File "mypy/checkexpr.py", line 6127, in accept_maybe_cache
  File "mypy/nodes.py", line 2469, in accept
  File "mypy/checkexpr.py", line 502, in visit_call_expr
  File "mypy/checkexpr.py", line 639, in visit_call_expr_inner
  File "mypy/checkexpr.py", line 1489, in check_call_expr_with_callee_type
  File "mypy/checkexpr.py", line 1593, in check_call
  File "mypy/checkexpr.py", line 2749, in check_overload_call
  File "mypy/checkexpr.py", line 2917, in infer_overload_return_type
  File "mypy/checkexpr.py", line 1582, in check_call
  File "mypy/checkexpr.py", line 1747, in check_callable_call
  File "mypy/checkexpr.py", line 2060, in infer_function_type_arguments_using_context
  File "mypy/checkexpr.py", line 3292, in apply_generic_arguments
  File "mypy/applytype.py", line 115, in apply_generic_arguments
  File "mypy/applytype.py", line 79, in get_target_type
  File "mypy/subtypes.py", line 189, in is_subtype
  File "mypy/subtypes.py", line 363, in _is_subtype
  File "mypy/types.py", line 2818, in accept
  File "mypy/subtypes.py", line 798, in visit_tuple_type
  File "mypy/typeops.py", line 119, in tuple_fallback
NotImplementedError:
mre.py:12: note: use --pdb to drop into pdb
```

A commenter found it also crashes with the old alias syntax and a forward reference:

```python
from __future__ import annotations
from collections import deque
from typing import Unpack

Inner = tuple[int, str]
Outer = tuple[bool, Unpack[Inner]]

class K:
    x: Base
    q: deque[Outer] = deque()

class Base: ...
```

To run mypy's type-check tests (see `CONTRIBUTING.md`; there is no virtualenv here, use `uv`):
`uv run --no-project --python 3.13 --with-editable . --with attrs --with filelock --with lxml --with psutil --with pytest --with pytest-xdist --with setuptools --with tomli --with typing_extensions --with mypy_extensions --with pathspec --with librt --with "ast-serialize>=0.12.1,<1.0" python -m pytest -n 0 mypy/test/testcheck.py -k "check-python312 or check-typevar-tuple"`
