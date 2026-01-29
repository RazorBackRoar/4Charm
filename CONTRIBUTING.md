# Contributing to 4Charm

## Branching Strategy & Workflow

We follow a strict feature branch workflow to ensure the stability of the `main`
branch.

### The `main` Branch

- **Status:** Protected.
- **Rule:** **NEVER DELETE `main`**. It is the primary branch.
- **Usage:** Contains stable code. Do not commit directly to `main`; always use

  a Pull Request.

### Workflow

1. **Create a Feature Branch**
   - Naming convention: `feature/name-of-feature`, `fix/issue-description`, or

```text
`chore/task-name`.
```

- Example: `fix-ci-build`.

1. **Make Changes**
   - Commit your changes to your feature branch.

2. **Open a Pull Request**
   - Open a PR targeting `main`.
   - Ensure all checks pass (CI, Pylint).
   - Request review if required.

3. **Merge & Delete Feature Branch**
   - Once the PR is approved and merged, **delete the feature branch** (e.g.,

```text
`fix-ci-build`).
```

- **Do NOT delete `main`**.

## Branch Protection

This repository uses branch protection rules for `main`.

- **Require status checks to pass before merging.**
- **Require review from Code Owners.**
- **Include administrators.**
- **Restrict deletions.**

## Code Style

- We use `pylint` for linting.
- Follow PEP 8 guidelines.
