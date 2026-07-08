# Packaging And Publishing DICE

This project is packaged with the standard Python `pyproject.toml` flow.

The import package is still:

```python
import dice
```

The installed commands are still:

```powershell
dice
dice-daemon
```

The PyPI distribution name is:

```text
dice-chain-executor
```

The name `dice` is already used on PyPI by a dice-notation library, so publishing this project as
`dice` would collide with an existing package. Users should install this project with:

```powershell
python -m pip install dice-chain-executor
```

Then run:

```powershell
dice
```

## Local Editable Install

From the project root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,publish]"
```

Verify:

```powershell
python -m dice
dice --help
dice-daemon --help
python -m pytest
```

## Build A Release

Install the publishing tools:

```powershell
python -m pip install -e ".[publish]"
```

Clean old build output:

```powershell
Remove-Item -Recurse -Force build, dist
```

Build source distribution and wheel:

```powershell
python -m build
```

You should get files like:

```text
dist/dice_chain_executor-0.1.0.tar.gz
dist/dice_chain_executor-0.1.0-py3-none-any.whl
```

Check the package:

```powershell
python -m twine check dist/*
```

## Test The Built Wheel Locally

Create a fresh environment outside your development install:

```powershell
py -3.12 -m venv .venv-wheel-test
.\.venv-wheel-test\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install .\dist\dice_chain_executor-0.1.0-py3-none-any.whl
dice --help
dice-daemon --help
python -m dice
```

## Publish To TestPyPI

Create an account at:

```text
https://test.pypi.org
```

Create an API token, then upload:

```powershell
python -m twine upload --repository testpypi dist/*
```

Install from TestPyPI in a fresh environment:

```powershell
py -3.12 -m venv .venv-testpypi
.\.venv-testpypi\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --index-url https://test.pypi.org/simple --extra-index-url https://pypi.org/simple dice-chain-executor
dice --help
```

## Publish To PyPI

Create an account at:

```text
https://pypi.org
```

Create an API token scoped to the project if the project already exists, or scoped to your account
for the first upload.

Upload:

```powershell
python -m twine upload dist/*
```

After publishing, users can install with:

```powershell
python -m pip install dice-chain-executor
```

## Automatic GitHub To PyPI Publishing

This repository includes GitHub Actions workflows:

```text
.github/workflows/ci.yml
.github/workflows/publish.yml
```

`ci.yml` runs on normal pushes and pull requests. It installs DICE, runs tests, and verifies that the
package builds.

`publish.yml` runs when you push a version tag:

```text
v0.1.0
v0.1.1
v0.2.0
```

It builds the package and publishes to PyPI using PyPI Trusted Publishing. This means GitHub uses
OIDC to prove the workflow identity to PyPI, so you do not need to store a long-lived PyPI API token
in GitHub secrets.

### Configure PyPI Trusted Publishing

On PyPI, create or open the `dice-chain-executor` project, then add a GitHub Trusted Publisher.

Use these values:

```text
Owner: YOUR_GITHUB_USERNAME_OR_ORG
Repository name: YOUR_REPOSITORY_NAME
Workflow name: publish.yml
Environment name: pypi
```

The environment name matters because the workflow uses:

```yaml
environment:
  name: pypi
```

You can optionally configure the `pypi` environment in GitHub with required reviewers, so publishing
waits for approval before upload.

### Release From Git

Before publishing a new version, update:

```text
pyproject.toml
src/dice/__init__.py
```

Commit the version change:

```powershell
git add pyproject.toml src/dice/__init__.py
git commit -m "Release v0.1.1"
```

Create and push a matching tag:

```powershell
git tag v0.1.1
git push origin main
git push origin v0.1.1
```

The publish workflow checks that the tag version matches `pyproject.toml`. For example:

```text
tag: v0.1.1
pyproject.toml version: 0.1.1
```

If they do not match, the workflow stops before publishing.

After the workflow succeeds, users can install the new release:

```powershell
python -m pip install --upgrade dice-chain-executor
```

## Versioning

Before every release, update both:

```text
pyproject.toml
src/dice/__init__.py
```

For example:

```text
0.1.0
0.1.1
0.2.0
1.0.0
```

Use `0.x` while DICE is still changing quickly.

## Release Checklist

1. Update version in `pyproject.toml`.
2. Update version in `src/dice/__init__.py`.
3. Update `README.md` and docs if behavior changed.
4. Run tests:

```powershell
python -m pytest
```

5. Build:

```powershell
python -m build
```

6. Check:

```powershell
python -m twine check dist/*
```

7. Upload to TestPyPI.
8. Install from TestPyPI in a clean environment.
9. Upload to PyPI.
10. Install from PyPI in a clean environment.

## Important Naming Notes

`pip install dice` installs the existing PyPI package named `dice`, not this DICE project.

This project should use:

```powershell
python -m pip install dice-chain-executor
```

The command users run after installation is still:

```powershell
dice
```
