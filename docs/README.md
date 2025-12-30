# STCM2L Script Decompiler

Decompiles STCM2L binary script files to readable text for translation.

## Version

**Current: v1.1.15**

See `CHANGELOG.md` for version history.

## Project Structure

```
stcm2l/
├── stcm2l_decompiler.py    # Main decompiler script (current version)
├── SCRIPT/                  # Source STCM2L binary files
├── docs/                    # Documentation
│   ├── README.md           # This file
│   ├── STCM2L_FORMAT.md    # Binary format documentation
│   ├── CHANGELOG.md        # Version history
│   ├── VERSION_POLICY.md   # Version update guidelines
│   └── PROBLEMATIC_FILES.md # Known problematic files
├── release/                 # Code releases (archived versions)
│   ├── stcm2l_decompiler_v1.1.15.py  # v1.1.15 release
│   ├── stcm2l_decompiler.py.v1.1.14  # v1.1.14 archived
│   └── ...                 # Previous versions
└── extract/                 # Extracted/decompiled text files
    ├── decompiled_v1.1.15/ # Latest decompiled output
    ├── decompiled_v1.1.14/ # Previous versions
    └── ...
```

## Usage

```bash
# Show version
python stcm2l_decompiler.py --version

# Single file (outputs to current directory)
python stcm2l_decompiler.py SCRIPT/10

# Batch decompile all files to folder
python stcm2l_decompiler.py SCRIPT/ extract/decompiled_v1.1.15/
```

## Output Format

Each decompiled entry shows:

```
--- Entry N (Type: X) ---
Speaker: [character_name]
Text:
[Dialogue text with line breaks preserved]
```

Short labels are shown in brackets: `[label]`

## Examples

### Output Example

```
--- Entry 1 (Type: 11) ---
Speaker: yougo1
Text:
鼠種の騎士らによって構成された
騎士団。
体つきが小さいため、戦闘力は低
いが、その分諜報や暗殺といった
ところで役に立つ。
メヨーヨが重用している。 [ちゅーちゅーないつ]
```

### Command Examples

```bash
# Decompile single file to current directory
python stcm2l_decompiler.py SCRIPT/10

# Decompile all files to extract/ folder
python stcm2l_decompiler.py SCRIPT/ extract/decompiled_v1.1.15/

# Check version
python stcm2l_decompiler.py --version
```

## File Format

This decompiler supports two STCM2L formats:

| Format | Description | Example Files |
|--------|-------------|---------------|
| **Dialogue Format** | Speaker names + Japanese dialogue | 10, 101, 102, etc. |
| **Full STCM2L Format** | Bytecode with GLOBAL_DATA/CODE_START_ | 0, 1, etc. |

See `docs/STCM2L_FORMAT.md` for detailed format documentation.

## Requirements

- Python 3.6+

## Documentation Files

| File | Description |
|------|-------------|
| `docs/README.md` | Project overview (this file) |
| `docs/STCM2L_FORMAT.md` | Binary format documentation |
| `docs/CHANGELOG.md` | Version history |
| `docs/VERSION_POLICY.md` | Version update guidelines |
| `docs/PROBLEMATIC_FILES.md` | Known problematic files |

## Versioning

- **Major (X.0.0)**: Breaking changes, format rewrites
- **Minor (0.X.0)**: New features, new format support
- **Patch (0.0.X)**: Bug fixes, text extraction improvements

## Contributing

When making changes:

1. Update `__version__` in `stcm2l_decompiler.py`
2. Add entry to `docs/CHANGELOG.md`
3. Update `docs/STCM2L_FORMAT.md` if format discoveries were made
4. Test on file 10 (known good reference)
5. Archive old version to `release/` folder
6. Output to `extract/decompiled_vX.X.X/` folder

See `docs/VERSION_POLICY.md` for detailed guidelines.
