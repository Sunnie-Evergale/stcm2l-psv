# Release Workflow - STCM2L Decompiler

This document describes the standard workflow for releasing new versions of the STCM2L decompiler.

## Version Numbering

The decompiler uses **semantic versioning**: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes (rare)
- **MINOR**: New features (new entry types, new functionality)
- **PATCH**: Bug fixes (missing entries, parsing fixes)

Current version policy:
- Adding support for a new entry type = **PATCH** bump (e.g., 1.1.17 → 1.1.18)
- Fixing parsing bugs = **PATCH** bump
- New features = **MINOR** bump

## Pre-Release Checklist

Before making any release, verify:

1. [ ] Binary analysis completed (verified issue exists in actual binary)
2. [ ] Root cause identified
3. [ ] Fix scope understood (which files to modify)
4. [ ] No breaking changes introduced

## Release Steps

### 1. Update Code

**File: `stcm2l_decompiler.py`**

Update the version number (line ~35):
```python
__version__ = "1.1.XX"  # Increment version
```

Update the module docstring (lines 1-35):
```python
"""
STCM2L Script Decompiler v1.1.XX  # Update version here too

Changelog:
    v1.1.XX - [Brief description]
        - [Change 1]
        - [Change 2]
    v1.1.XX - [Previous version]
    ...
"""
```

**Add new entry type to ALL locations:**
1. Compact format validation (search: `if entry_type not in`)
2. Padded format validation (search: `if entry_type not in`)
3. Padded format next entry check (search: `if next_type in [`)
4. Combining logic - Line ~393: `if next_type not in (`
5. Combining logic - Line ~618: `if current_type in (`
6. Combining logic - Line ~629: `elif prev_type in (`
7. Combining logic - Line ~667: `if next_type not in (`

**IMPORTANT:** If the new type has special behavior (like Type 0x10's placeholder size), add special handling.

### 2. Update Documentation

**File: `docs/CHANGELOG.md`**

Add new version entry at the TOP of the file:
```markdown
## [1.1.XX] - YYYY-MM-DD

### Fixed
- **[Issue title]**: [Description]
  - Root cause: [Technical explanation]
  - File XXX: [Specific example of the bug]
  - Binary analysis confirmed: [Details]
  - [Solution]

### Changed
- [Change 1]
- [Change 2]

### Example of Recovered Entry (File XXX, Entry N)
**v1.1.XX (before):**
```
[Show incorrect output]
```

**v1.1.XX (after):**
```
[Show corrected output]
```

**Finding:** [Technical conclusion]

## [1.1.XX-1] - YYYY-MM-DD  <-- Previous version
```

**File: `docs/STCM2L_FORMAT.md`**

Add the new entry type to the table (around line 230-250):
```markdown
| 0xXX | [Type Name] | "[Example]" | [Action] (v1.1.XX) |
```

### 3. Recompile ALL Files

**CRITICAL:** Always recompile to the VERSIONED folder, NOT a test file!

```bash
python3 stcm2l_decompiler.py SCRIPT/ extract/decompiled_v1.1.XX/
```

**Do NOT use:**
```bash
# WRONG - This creates a test file, not a versioned folder
python3 stcm2l_decompiler.py SCRIPT/106 extract/test_106.txt
```

The `OUTPUT_DIR` variable in the code automatically creates:
```python
OUTPUT_DIR = f"decompiled_v{__version__}"
# If __version__ = "1.1.19", OUTPUT_DIR = "decompiled_v1.1.19"
```

### 4. Verify Results

Check entry count for affected files:
```bash
# Count entries
grep -c "Entry " extract/decompiled_v1.1.XX/106.txt

# Verify specific text is present
grep "specific text" extract/decompiled_v1.1.XX/106.txt

# Count new entry type occurrences
grep -c "Type: YY" extract/decompiled_v1.1.XX/106.txt
```

Compare with previous version:
```bash
# Previous version entry count
grep -c "Entry " extract/decompiled_v1.1.XX-1/106.txt

# New version entry count
grep -c "Entry " extract/decompiled_v1.1.XX/106.txt
```

### 5. Commit Changes (if using git)

```bash
git add stcm2l_decompiler.py docs/CHANGELOG.md docs/STCM2L_FORMAT.md
git commit -m "v1.1.XX: [Brief description]"
git tag v1.1.XX
```

## Common Mistakes to Avoid

### Mistake 1: Forgetting to update all type lists
**Symptom:** Entry count drops instead of increasing
**Cause:** Added new type to validation but forgot combining logic
**Fix:** Add to ALL 7 locations listed in Step 1

### Mistake 2: Using test file instead of versioned folder
**Symptom:** No extract/decompiled_v1.1.XX/ folder created
**Cause:** Used `extract/test_106.txt` instead of `extract/decompiled_v1.1.19/`
**Fix:** Always use folder path ending with `/`

### Mistake 3: Not updating changelog version
**Symptom:** Changelog has wrong version number
**Cause:** Copied previous entry but forgot to update version
**Fix:** Double-check all version numbers in changelog

### Mistake 4: Special size handling not implemented
**Symptom:** Entry count drops significantly (e.g., 1201 → 644)
**Cause:** New entry type has special size field (like Type 0x10's 0x4000 placeholder)
**Fix:** Check binary structure carefully - if size > 10000, needs special handling

## Post-Release Verification

After release, verify:

1. [ ] `extract/decompiled_v1.1.XX/` folder exists
2. [ ] Entry count increased or stayed same (never decreases)
3. [ ] New entry type appears in output
4. [ ] Specific bug is fixed
5. [ ] No regressions in other files

## Quick Reference

### Version Locations
- `stcm2l_decompiler.py` line ~35: `__version__ = "X.Y.Z"`
- `stcm2l_decompiler.py` line ~3: Docstring header
- `docs/CHANGELOG.md`: Add new entry at TOP
- `docs/STCM2L_FORMAT.md`: Add to entry types table

### Type List Locations (7 total)
1. Compact format validation: `if entry_type not in [`
2. Padded format validation: `if entry_type not in [`
3. Padded format next entry check: `if next_type in [`
4. Combining logic line ~393: `if next_type not in (`
5. Combining logic line ~618: `if current_type in (`
6. Combining logic line ~629: `elif prev_type in (`
7. Combining logic line ~667: `if next_type not in (`

### Recompile Command
```bash
python3 stcm2l_decompiler.py SCRIPT/ extract/decompiled_v1.1.XX/
```

### Verify Command
```bash
grep -c "Entry " extract/decompiled_v1.1.XX/106.txt
```
