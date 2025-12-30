# Version Policy

This document describes how to manage version updates for the STCM2L Decompiler.

## Version Number Format

We use [Semantic Versioning](https://semver.org/spec/v2.0.0.html): `MAJOR.MINOR.PATCH`

- **MAJOR (X.0.0)**: Breaking changes
  - Output format changes that break compatibility
  - API changes
  - Format rewrites requiring user migration

- **MINOR (0.X.0)**: New features
  - New file format support
  - New speaker character types
  - New output options
  - Format discoveries that add new entry types

- **PATCH (0.0.X)**: Bug fixes
  - Text extraction improvements
  - Better handling of edge cases
  - Performance optimizations
  - Documentation updates

## Version Update Process

When making changes to the decompiler:

### Step 1: Determine Version Bump Type

| Change Type | Version Bump | Example |
|-------------|--------------|---------|
| Breaking changes (output format, API) | MAJOR | 1.0.0 → 2.0.0 |
| New features, new format support | MINOR | 1.0.0 → 1.1.0 |
| Bug fixes, text extraction improvements | PATCH | 1.0.0 → 1.0.1 |

### Step 2: Update Code

Before committing changes:

1. **Update `__version__` in `stcm2l_decompiler.py`**

   ```python
   __version__ = "1.0.1"  # or 1.1.0 or 2.0.0
   ```

2. **Update module docstring** (if significant changes)

   ```python
   """
   STCM2L Script Decompiler v1.0.1

   Changelog:
       v1.0.1 - Fixed UTF-8 handling for multi-byte characters
   """
   ```

### Step 3: Update Documentation

1. **Add entry to `CHANGELOG.md`**

   ```markdown
   ## [1.0.1] - 2025-12-28

   ### Fixed
   - Better handling of multi-byte UTF-8 characters
   - Fixed text extraction for entries with unusual padding

   ### Tested Files
   - 115/119 SCRIPT files successfully processed
   ```

2. **Update `STCM2L_FORMAT.md`** if format discoveries were made

   ```markdown
   ## New Findings (v1.0.1)
   - Discovered entry type 3 = choice/branch points
   - New speaker prefix: `lizz0*`
   ```

### Step 4: Test

Before finalizing:

- [ ] Version number updated in code
- [ ] Changelog entry added with date
- [ ] Format docs updated if applicable
- [ ] **Test on file 10** (known good reference file)
- [ ] Document any new speaker prefixes found
- [ ] Run batch decompilation to verify no regressions

### Step 5: Release Notes Template

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added/Fixed/Changed
- Description of change

### Format Updates
- Any new format discoveries (entry types, speaker prefixes, etc.)

### Test Results
- X/Y files successfully processed
- Any new known limitations
```

## Version Bump Checklist

Use this checklist before each release:

- [ ] `__version__` updated in `stcm2l_decompiler.py`
- [ ] Module docstring updated (if needed)
- [ ] `CHANGELOG.md` entry added with date
- [ ] `STCM2L_FORMAT.md` updated (for format changes)
- [ ] `README.md` updated (for user-facing changes)
- [ ] Tested on file 10 (reference file)
- [ ] Tested batch decompilation
- [ ] `PROBLEMATIC_FILES.md` updated (if applicable)

## Quick Reference

### Common Scenarios

| Scenario | Type | Example |
|----------|------|---------|
| Fix text extraction bug | PATCH | 1.0.0 → 1.0.1 |
| Add new speaker prefix | PATCH | 1.0.0 → 1.0.1 |
| Discover new entry type | MINOR | 1.0.0 → 1.1.0 |
| Support completely new format | MAJOR | 1.0.0 → 2.0.0 |
| Change output format | MAJOR | 1.0.0 → 2.0.0 |
| Add command-line option | MINOR | 1.0.0 → 1.1.0 |
| Improve performance | PATCH | 1.0.0 → 1.0.1 |

## Examples

### Example 1: Bug Fix (PATCH)

```
Version: 1.0.0 → 1.0.1

CHANGELOG.md entry:
## [1.0.1] - 2025-12-28
### Fixed
- Fixed crash on files with unusual entry padding
```

### Example 2: New Feature (MINOR)

```
Version: 1.0.0 → 1.1.0

CHANGELOG.md entry:
## [1.1.0] - 2025-12-29
### Added
- Support for entry type 12 (internal monologue)
- New speaker prefix: `lizz0*`
```

### Example 3: Breaking Change (MAJOR)

```
Version: 1.0.0 → 2.0.0

CHANGELOG.md entry:
## [2.0.0] - 2025-12-30
### Changed
- Output format now uses JSON instead of plain text
- Speaker names moved to metadata field
```
