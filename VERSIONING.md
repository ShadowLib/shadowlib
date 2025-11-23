# Versioning and Release Process

ShadowLib uses automated semantic versioning with conventional commits.

## How It Works

### 1. Commit Format Determines Version Bump

```bash
# PATCH bump (1.0.0 → 1.0.1)
fix: resolve inventory crash
perf: optimize cache lookups
docs: update API documentation

# MINOR bump (1.0.0 → 1.1.0)
feat: add new equipment module
feat(bank): implement deposit all functionality

# MAJOR bump (1.0.0 → 2.0.0)
feat!: redesign API structure
fix!: change return type of getItems()
# OR
feat: redesign API

BREAKING CHANGE: getItems() now returns Item objects instead of IDs
```

### 2. Automated Release Workflow

When you push to `main`:

1. **Semantic-release analyzes commits**
   - Determines version bump type
   - Generates release notes

2. **Updates version files**
   - `pyproject.toml` version field
   - `shadowlib/__init__.py` __version__
   - `CHANGELOG.md` with new entry

3. **Creates git tag and GitHub release**
   - Tags commit with new version (v2.0.0)
   - Creates GitHub release with notes

4. **Builds and publishes to PyPI**
   - Builds package with new version
   - Publishes to PyPI automatically

## Correct Workflow

### Step 1: Make Changes

```bash
# Work on your feature
git checkout -b feat/new-feature
# ... make changes ...
```

### Step 2: Commit with Conventional Format

```bash
# Use conventional commit format
git add .
git commit -m "feat(module): add new functionality"
```

### Step 3: Push to Main

```bash
# Either merge PR or push directly
git push origin main
```

### Step 4: Automatic Release

The GitHub Actions workflow will:
- Determine new version based on commits
- Update pyproject.toml and __init__.py
- Create CHANGELOG entry
- Build package with NEW version
- Publish to PyPI

## Version Synchronization

✅ **Correct Flow:**
1. Commit with conventional format
2. Semantic-release determines version
3. Updates pyproject.toml
4. Builds package with updated version
5. Publishes to PyPI

❌ **Old Flow (Fixed):**
1. Build package (old version)
2. Semantic-release updates version
3. Publish old version to PyPI

## Checking Version

```bash
# In pyproject.toml
version = "2.0.0"

# In shadowlib/__init__.py
__version__ = "2.0.0"

# On PyPI
pip install shadowlib==2.0.0
```

## Manual Release (Not Recommended)

If you need to release manually:

```bash
# 1. Update version in pyproject.toml and __init__.py
# 2. Update CHANGELOG.md
# 3. Commit and tag
git add .
git commit -m "chore(release): 2.0.0 [skip ci]"
git tag v2.0.0
git push origin main --tags

# 4. Build and publish
python -m build
twine upload dist/*
```

## Troubleshooting

### Version Mismatch

If PyPI version doesn't match git tags:

1. Check GitHub Actions logs: https://github.com/ShadowLib/shadowlib/actions
2. Verify PYPI_TOKEN secret is set correctly
3. Check if semantic-release created the tag
4. Manually trigger release if needed

### Failed PyPI Upload

If upload fails:
- Version might already exist (use `--skip-existing`)
- PYPI_TOKEN might be invalid
- Package might not build correctly

## Best Practices

1. **Always use conventional commits** on main branch
2. **Test locally** before pushing to main
3. **Let automation handle versioning** - don't manually edit version numbers
4. **Monitor GitHub Actions** after pushing to main
5. **Check PyPI** to verify new version appears

## References

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [Semantic Release](https://github.com/semantic-release/semantic-release)
