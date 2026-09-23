# Working in this repository

## Run the checks locally

CI no longer runs the tests. Actions here only dispatches the submodule pin
update to `claude-2` after a merge. Run the suite yourself before opening or
updating a pull request:

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements-test.txt
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -v
```

The dependency step is not optional: `tests/test_render.py` imports `pymupdf`,
and without it the suite reports a single import error rather than running. The
rendering itself needs WeasyPrint's system libraries, which Homebrew supplies on
macOS; the deleted workflow installed the Debian equivalents on its runner.

It must exit 0. Last verified on a macOS controller: Ran 3 tests in 18.1s, OK.

The rule this follows, and why, is [`ci-rule.md`](https://github.com/asabirov/org/blob/main/ci-rule.md)
in `asabirov/org`. Nothing stops a broken commit reaching `main` here — the
suite is the only gate, so run it.
