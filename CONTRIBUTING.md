# Contributing Guide

Thank you for your interest in improving Climate Data Extraction.

## Development Setup

1. Create a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run tests:

```bash
pytest -v
```

## Contribution Standards

- Keep changes focused and well-scoped.
- Add or update tests for behavioral changes.
- Update documentation when modifying public behavior.
- Use clear commit messages in imperative style.

## Pull Request Checklist

- Code runs locally without errors.
- Tests pass (`pytest`).
- README/docs updated if needed.
- No secrets or credentials are committed.

## Reporting Issues

When opening an issue, include:

- Expected behavior
- Actual behavior
- Reproduction steps
- Environment details (OS, Python version)
