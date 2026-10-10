Please address this maintainer report in Pydantic.

**Refactor model namespace inspection**

## Change Summary

In the model metaclass, prior to the class being created, we fetch annotations to perform checks. This is a bit fragile (although the logic in this PR still is fragile for annotations _not_ fully evaluated) because in Python < 3.14, we fetch the raw `__annotations__`, and in Python >= 3.14, this requires evaluating annotations (and we'll end up doing it again in `collect_model_fields()`). An added test show a case where we now correctly classify an attribute as being private.

This also unifies exceptions to use `PydanticUserError` instead of bare `TypeError`/`NameError`.

Keep existing model behavior working, including private attributes and namespace errors. Add regression coverage. You can run tests with `.venv/bin/python -m pytest tests/test_private_attributes.py tests/test_fields.py tests/test_main.py tests/test_parse.py`; the dependencies are installed.
