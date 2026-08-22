# Contributing to Agents

Thanks for helping improve this repository.

## Before you start

- Read `README.md` for the project layout and setup steps.
- Check for existing issues or discussions before starting new work.
- Prefer small, focused pull requests.

## Local setup

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Development expectations

- Keep changes scoped to the problem being solved.
- Do not mix unrelated refactors with functional fixes.
- Update documentation when behavior, interfaces, or workflow expectations change.
- Add or update tests when changing runtime behavior.

## Validation

Run the existing test suite before opening a pull request:

```bash
python3 -m pytest -q
```

If you changed only a narrow area, also run the most relevant targeted tests when practical.

## Pull requests

- Use a clear title that explains the change.
- Explain the problem, the solution, and any testing performed.
- Link related issues when applicable.
- Be responsive to review feedback and follow-up questions.

## Security

Do not include secrets, API keys, tokens, or private credentials in code, tests, screenshots, or logs.

If you discover a security issue, follow `SECURITY.md` instead of opening a public issue.
