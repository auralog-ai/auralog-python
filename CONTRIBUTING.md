# Contributing to auralog (Python SDK)

Thanks for your interest in improving the Auralog Python SDK! This guide covers the basics.

## Scope

This repo is the **Python SDK** only. For issues with the Auralog service itself (ingest, dashboard, analysis, billing), head to [auralog.ai](https://auralog.ai) or the [docs](https://docs.auralog.ai).

## Reporting bugs

Open a [bug report](https://github.com/auralog-ai/auralog-python/issues/new?template=bug_report.yml). Include SDK version, Python version, minimal repro, expected vs. actual.

## Suggesting features

Open a [feature request](https://github.com/auralog-ai/auralog-python/issues/new?template=feature_request.yml). Describe the use case first, the proposed API second.

## Security issues

**Please don't open public issues for vulnerabilities.** See [SECURITY.md](./SECURITY.md) for how to report them privately.

## Development setup

Requirements: Python 3.10 or later.

```bash
git clone https://github.com/auralog-ai/auralog-python.git
cd auralog-python
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
pytest
```

## Checks

Before opening a PR, run the full suite locally:

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

CI runs these across Python 3.10, 3.11, 3.12, 3.13.

## Commit messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — new feature
- `fix:` — bug fix
- `docs:` — documentation only
- `test:` — tests only
- `refactor:` — code change that neither fixes a bug nor adds a feature
- `build:` — build system, CI, dependencies
- `chore:` — other housekeeping (e.g., release commits)

## Releases

Maintainers publish via GitHub Releases. Tagging `vX.Y.Z` and publishing a release triggers the `Release` workflow, which builds sdist + wheel and publishes to PyPI via OIDC Trusted Publisher — no manual `twine upload` needed.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](./LICENSE).
