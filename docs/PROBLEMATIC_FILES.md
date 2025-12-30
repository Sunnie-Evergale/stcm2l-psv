# Problematic STCM2L Files

Files that failed to decompile or produced minimal output.

## Investigation Status

### Files with 0 Entries (v1.0.0)

| File | Size | Issue | Status |
|------|------|-------|--------|
| 20 | ~35KB | Speaker patterns not in hardcoded list | Open |
| 30 | ~35KB | Speaker patterns not in hardcoded list | Open |
| 40 | ~35KB | Speaker patterns not in hardcoded list | Open |
| 50 | ~35KB | Speaker patterns not in hardcoded list | Open |
| 60 | ~35KB | Speaker patterns not in hardcoded list | Open |

## Root Cause (v1.0.0)

Files 20, 30, 40, 50, 60 have different speaker name patterns that are not in the hardcoded prefix list:

**Current hardcoded prefixes:**
- `yougo*`, `her01*`, `zara0*`, `ness0*`, `pear0*`, `rich0*`, `rath0*`, `elza0*`, `tiara*`, `riche*`, `haniy*`

**Found in problematic files:**
- `bg1058a` - Background/scene identifier? (file 20)
- `rath02` - Character "rath" with numeric suffix (file 20)
- `rath02_tujo` - Compound speaker name (file 20)

### Sample Entry from File 20

```
Header: fb00 0000 0800 0000 (251 entries)
Speaker: bg1058a
Text: (Japanese text found at offset 0x170)
```

## Resolution Notes

### Possible Fixes

1. **Expand hardcoded prefix list** - Add more patterns like `bg*`, `rath*`, etc.
2. **Pattern-based detection** - Detect entry headers without filtering by speaker prefix
3. **User-specified prefixes** - Allow users to provide additional patterns via config

### Estimated Fix

Minor version update (1.0.0 → 1.0.1 or 1.1.0):
- Add wildcard-based speaker detection
- Or expand hardcoded list to include discovered patterns

## Changelog

| Version | Action | Notes |
|---------|--------|-------|
| v1.0.0 | Identified | 5 files fail due to missing speaker patterns |
| ? | To fix | Implement pattern relaxation or add new prefixes |
