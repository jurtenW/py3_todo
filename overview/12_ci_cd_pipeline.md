# CI/CD Pipeline

## Overview

The project uses **GitHub Actions** for continuous integration. The pipeline runs on every push to `main`, `master`, or `develop`, and on every pull request.

## Workflow Configuration

File: `.github/workflows/ci.yml`

```yaml
name: CI
on:
  push:
    branches: [main, master, develop]
  pull_request:
    branches: [main, master, develop]
```

## Jobs

### Test Matrix

The `test` job runs on **Ubuntu LTS** across **4 Python versions**:

| Python Version | Status |
|---|---|
| 3.10 | Minimum supported |
| 3.11 | Current stable |
| 3.12 | Latest |
| 3.13 | Development |

The `fail-fast: false` setting means all versions run to completion even if one fails. This gives a complete picture of compatibility.

### Steps

Each Python version runs these steps sequentially:

1. **Checkout**: `actions/checkout@v4` clones the repository.
2. **Setup Python**: `actions/setup-python@v5` installs the specified Python version.
3. **Install Dependencies**:
   ```bash
   python -m pip install --upgrade pip
   pip install -e ".[dev]"
   ```
   The `-e` flag installs the package in **editable mode**, meaning changes to the source files are immediately reflected without reinstalling. `.[dev]` installs the optional `dev` dependencies (pytest, mypy, ruff, pytest-cov).
4. **Run Tests**:
   ```bash
   pytest --cov=clicktodo --cov-report=term-missing --cov-fail-under=80
   ```
   - `--cov=clicktodo`: Measure coverage for the `clicktodo` package.
   - `--cov-report=term-missing`: Show which lines are missing coverage.
   - `--cov-fail-under=80`: Fail if coverage drops below 80%.
5. **Type Check**:
   ```bash
   mypy src/clicktodo
   ```
   Static type checking with mypy. Catches type errors without running the code.
6. **Lint**:
   ```bash
   ruff check src/
   ```
   Fast linter that checks for code style issues, unused imports, and modernization opportunities.

## Quality Gates

The pipeline enforces three quality gates:

| Gate | Tool | Threshold |
|---|---|---|
| Tests pass | pytest | All tests must pass |
| Coverage | pytest-cov | >= 80% line coverage |
| Types | mypy | No type errors |
| Style | ruff | No lint errors |

If any gate fails, the CI check fails and the PR cannot be merged (assuming branch protection is configured).

## Theory: Continuous Integration

**Continuous Integration (CI)** is the practice of automatically building and testing code changes. Benefits:

1. **Early Bug Detection**: Bugs are caught immediately after they're introduced, not weeks later during manual testing.
2. **Regression Prevention**: The test suite catches unintended side effects of changes.
3. **Confidence**: Developers can refactor with confidence, knowing the tests will catch breakage.
4. **Documentation**: The tests serve as executable documentation of expected behavior.

### Why Test Against Multiple Python Versions?

Python releases a new version every year. Testing against multiple versions ensures:
- The package works on the minimum supported version (3.10).
- The package works on the latest version (3.13).
- New Python features don't break compatibility with older versions.

### Why Use a Test Matrix?

A **test matrix** runs the same tests across multiple configurations (OS, Python version, etc.). This catches platform-specific bugs:

- A bug might only appear on Python 3.10 because of a behavior change in 3.11.
- A bug might only appear on Ubuntu because of a platform-specific library.

The matrix approach ensures comprehensive coverage without duplicating workflow definitions.

## Theory: Editable Installs

The `-e` flag in `pip install -e .` creates an **editable install**:

```bash
pip install -e ".[dev]"
```

This creates a link from the installed package location to the source directory. Changes to source files are immediately reflected without reinstalling. This is the standard development workflow:

```
source/                pip install -e .              site-packages/
├── clicktodo/   ──────────────────────────────►  ├── clicktodo/ ──► (symlink to source/)
│   ├── models.py                                       ├── models.py
│   ├── store.py                                        ├── store.py
```

Without editable mode, you'd need to run `pip install .` after every change.

## Theory: Static Type Checking (mypy)

**mypy** performs static type checking without running the code. It reads type annotations and verifies that types are used consistently:

```python
def todo_counts(data: dict[str, Any]) -> tuple[int, int]:
    ...
```

mypy verifies that `todo_counts` returns a `tuple[int, int]`. If you accidentally return a `list`, mypy catches it at analysis time, not runtime.

The configuration in `pyproject.toml`:

```toml
[tool.mypy]
packages = ["clicktodo"]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # Allow gradual typing
```

`disallow_untyped_defs = false` enables **gradual typing** -- you can add types incrementally without mypy failing on untyped functions. This is practical for evolving codebases.
