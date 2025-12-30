# STCM2L File Format Documentation

This document describes the binary structure of STCM2L script files used in the game.

## Format Overview

Two distinct STCM2L formats have been identified:

| Format | Description | Example Files |
|--------|-------------|---------------|
| **Dialogue Format** | Contains speaker names and Japanese dialogue text | 10, 101, 102, 103, 104, 105, etc. |
| **Full STCM2L Format** | Contains bytecode with GLOBAL_DATA and CODE_START_ sections | 0, 1, etc. |

---

## Dialogue Format Structure

### File Header

```
Offset  Size    Description
------  ----    -----------
0x00    4       Entry count (little-endian uint32)
0x04    4       Unknown/flags (usually 8)
```

### Entry Structure (Dialogue Format)

Each entry is variable-length and contains:

```
Offset  Size    Description
------  ----    -----------
+0x00   4       Entry header: type (2 bytes) + index (2 bytes)
+0x04   ~40     Speaker name area (null-terminated ASCII, 0xFF padded)
+var    var     Text segment 1 (short label/keyword)
+var    var     Padding (0x00 or 0xFF bytes)
+var    var     Text segment 2 (main dialogue with #n line breaks)
+var    var     Additional text segments (optional)
```

### Entry Header

| Field | Size | Description |
|-------|------|-------------|
| Type | 2 bytes | Entry type (little-endian). Common values: 1, 2, 11 |
| Index | 2 bytes | Entry sequence number (little-endian): 1, 2, 3... |

### Speaker Name Detection

Speaker names start with predictable prefixes:
- `yougo*` - Player character dialogue (yougo1, yougo2, etc.)
- `her01*` - Character "her01" variations
- `zara0*` - Character "zara" variations
- `ness0*` - Character "ness" variations
- `pear0*` - Character "pearl" variations
- `rich0*` - Character "richie" variations
- `rath0*` - Character "rath" variations
- `elza0*` - Character "elza" variations

### Text Segments

Each entry contains multiple text segments separated by null bytes (0x00) or padding (0xFF):

| Segment | Description | Example |
|---------|-------------|---------|
| Segment 1 | Short label/keyword | "ＣＣＫ", "亜人種" |
| Segment 2 | Main dialogue | Full sentences with #n line breaks |
| Additional | Optional extra text | Varies |

**Key Finding**: The longest text segment is typically the main dialogue.

### Text Encoding

- **Encoding**: UTF-8
- **Line breaks**: Marked as `#n` in binary, should be converted to newlines
- **Padding**: 0x00 or 0xFF bytes between segments

### Bytecode Instructions (to skip)

These patterns appear in entries but are not dialogue:

| Pattern | Type | Description |
|---------|------|-------------|
| `memory_init` | Instruction | Memory initialization |
| `memory_exit` | Instruction | Memory cleanup |
| `COLLECTION_LINK` | Instruction | Data reference |
| `scene_play` | Instruction | Scene playback |
| `suma` | Variable | Unknown variable |
| `@X!` | Instruction | Control commands (X = any byte) |
| `switch` | Control flow | Conditional branching |
| `case` | Control flow | Switch case statements |
| `default` | Control flow | Default case statements |
| `bgXXXX` | Background | Scene background references (X = hex digit) |
| `@commands` | Bytecode | @ prefixed control instructions |
| `edga01`, etc. | Character ID | Speaker/character reference codes |
| `ef_*` (v1.0.3) | Effect code | Screen/effects commands (ef_shake5, ef_flash, etc.) |
| `select` (v1.0.3) | UI element | Button/choice UI text |
| `export_data` (v1.0.3) | Export marker | Data export reference |

### Bytecode Identifiers (FILTER OUT)

These patterns indicate bytecode/system data, not dialogue:

| Pattern | Description | Example |
|---------|-------------|---------|
| `Release_` | Release flags | `Release_Flag` |
| `Rute_count_` | Route counter | `Rute_count_Mejojo` |
| `Fav[A-Z]` | Favorite character flags | `FavZara`, `FavPearl` |
| `LH_sel_` | Selection flags | `LH_sel_Route` |
| `sure\d*` | Sure/confidence flags | `sure1`, `sure60` |
| `rathL`, `elzaL`, `zara0`, `ness0` | Partial character IDs | Bytecode references |
| `her\d+`, `zk\d+` | Character reference codes | `her01`, `zk02` |
| `[A-Z][a-z]+_(bad|good)_end` | Route endings | `Rath_bad_end`, `Arles_good_end` |
| `TrueEnd` | True ending flag | Route ending marker |
| `[A-Z][a-z]+_[A-Za-z_]+` | System identifiers | `Bad_PandR`, `FavPearl` |
| `[a-z]+\d+_[a-z]+` | Complex variables | `mejo07_kamae`, `rath02_ucho` |
| `[a-z]+\d+` | Simple character IDs | `mejo07`, `rath02` (v1.1.2) |
| `[a-z]+\d+[a-z]*_[a-z]+` | Extended variable format | `raths01ht_kana` (v1.1.2) |
| `[a-z]{3,5}` | Short bytecode identifiers | `cck`, `suma`, etc. (v1.1.2) |

### Character Name Indicators (KEEP in output)

| Pattern | Type | Description |
|---------|------|-------------|
| `#Name[X]` | Placeholder text | Runtime variable placeholder for character names (X = number) |

**IMPORTANT**: Based on binary analysis (File 103), `#Name[X]` is **NOT** a separate binary field or speaker marker. It is **literally part of the UTF-8 text data** stored in the entry.

#### Binary Structure of #Name[X] Entries

**Type 0x03 entries** - Pure placeholder entries:
```
Offset     Hex                              Decoded
-------    ------------------------------  -------
0x1D558    03 00 00 00                     Type = 0x03
0x1D55C    01 00 00 00                     Index = 1
0x1D560    0c 00 00 00                     Size = 12 (8 bytes + padding)
0x1D564    23 4e 61 6d 65 5b 31 5d         Data: "#Name[1]\0"
```

**Type 0x0D entries** - Text with embedded placeholder:
```
Offset     Hex                              Decoded
-------    ------------------------------  -------
0x1E914    0d 00 00 00                     Type = 0x0D
0x1E918    01 00 00 00                     Index = 1
0x1E91C    34 00 00 00                     Size = 52
0x1E920    234e 616d 655b 315d e381 a1...  Data: "#Name[1]ちゃんは今日を..."
```

The `#Name[X]` placeholder is **part of the dialogue text** itself, not a separate field. The game engine replaces these placeholders with actual character names at runtime.

These are **preserved** in the output for translators to see the original structure.

---

## Full STCM2L Format Structure

### File Header

```
Offset  Description
------  -----------
0x00    "STCM2L" magic string (6 bytes)
0x06    Timestamp: "May 30 2012 14:17:58" (ASCII)
0x1E    Unknown (4 bytes)
0x2C    Padding
```

### Sections

| Offset | Section | Description |
|--------|---------|-------------|
| 0x50 | GLOBAL_DATA | Global variable/data section |
| 0x260 | CODE_START_ | Bytecode instructions section |

### Dialogue Splitting in Full STCM2L Format

In Full STCM2L format files (like 103), dialogue lines are stored as **separate null-terminated strings** even when they form a continuous sentence.

#### Why This Happens

The binary format stores each line as a separate string for flexibility:
- The game engine can display lines one at a time
- Text effects can be applied per line
- Timing/pacing can be controlled per string

#### Example

Binary structure (simplified):
```
0x1000: "I never thought about it too deeply.\0"
0x1040: "#Name[1]\0"                   ← Show character name overlay
0x104C: "(After all, he treats me more kindly\0"
0x1090: "than a real brother ever would.)\0"
```

For translators, these should be combined into:
```
"I never thought about it too deeply."
"#Name[1]
(After all, he treats me more kindly than a real brother ever would.)"
```

#### #Name[X] Indicators

The `#Name[X]` patterns are character name indicators that tell the game which character is speaking. These are **preserved** in the decompiled output on their own line before the dialogue text, acting as speaker labels for translators.

---

## Structured Entry Format (v1.0.2 Discovery)

### Entry Header Structure (Full Format)

In the CODE_START_ section, entries follow a structured format:

```
Offset  Size    Description
------  ----    -----------
+0x00   4       Padding (00 00 00 00)
+0x04   4       Entry Type (little-endian uint32)
+0x08   4       Entry Index (little-endian uint32)
+0x0C   4       Entry Size (little-endian uint32)
+0x10   var     String Data (UTF-8, null-terminated)
```

### Entry Types (Structured Format)

| Type Value | Description | Example Content | Action |
|------------|-------------|-----------------|--------|
| 0x01 | English Choice Options | "Yes", "No", "OK", "Cancel" | Convert to Type 0x02, group as choices (v1.1.13) |
| 0x02 | Speaker Name / Bytecode | "Pearl", "Richie", "bg96", "suma" | Speaker names: KEEP, Bytecode: FILTER |
| 0x03 | Speaker Name / Choice Options | "Pearl", "パール", "はい" | Speaker names: KEEP, Bytecode: FILTER |
| 0x04 | Dialogue Text | "ふぅん。", "ぅ、ン。" | KEEP as dialogue |
| 0x05 | Dialogue Continuation | "Come on, #Name[1]," | KEEP as dialogue part |
| 0x06 | Dialogue Continuation | "a Lobeira." | KEEP as dialogue part (v1.1.5) |
| 0x07 | Dialogue Continuation | "lets go outside right now!" | KEEP as dialogue part, now combines with Type 0x05/0x06/etc. (v1.1.15) |
| 0x08 | Dialogue Text | Various dialogue lines | KEEP as dialogue (v1.1.10) |
| 0x09 | Dialogue Text | "Before the guests arrive, you three" | KEEP as dialogue (v1.1.11) |
| 0x0A | Dialogue Text | Various dialogue lines | KEEP as dialogue (v1.1.9) |
| 0x0B | Dialogue Text | Various dialogue lines | KEEP as dialogue (v1.1.7) |
| 0x0C | Dialogue Text | Various dialogue lines | KEEP as dialogue (v1.1.7) |
| 0x0D | Dialogue Continuation | "will have to change, along with other preparations." | KEEP as dialogue part (v1.1.15) |
| 0x0E | Dialogue Continuation | "Take that into account while y..." | KEEP as dialogue part (v1.1.15) |
| 0x0F | Dialogue Continuation | "his clothing. Unperturbed, the young man..." | KEEP as dialogue part (v1.1.16) |
| 0x10 | Dialogue Continuation | "啜り、傷口にむしゃぶりついて喉を鳴らす。" | KEEP as dialogue part (v1.1.18) - **Has special size field (placeholder 0x4000)** |
| 0x11 | Dialogue Continuation | "and then it was very gentle, and then your mouth cracked a smile." | KEEP as dialogue part (v1.1.19) |
| 0x12 | Narration | "Background music stops playing..." | KEEP as narration (no speaker) (v1.1.7) |

### Binary Example (Pearl/Richie from file 116 at 0x20d08)

```
Offset     Hex Bytes                                          Description
-------    ---------------------------------------------      -----------
0x20d08    00 00 00 00 02 00 00 00                             Padding + Type 0x02
0x20d10    01 00 00 00 08 00 00 00                             Index: 1, Size: 8
0x20d18    50 65 61 72 6C 00 00 00                             "Pearl\0\0\0"
0x20d20    00 00 00 00 04 00 00 00                             Padding + Type 0x04
0x20d28    01 00 00 00 10 00 00 00                             Index: 1, Size: 16
0x20d30    E3 81 B5 E3 81 85 E3 82 93 E3 80 82 00 00 00       "ふぅん。\0\0\0"
0x20d40    00 00 00 00 02 00 00 00                             Padding + Type 0x02
0x20d48    01 00 00 00 08 00 00 00                             Index: 1, Size: 8
0x20d50    52 69 63 68 69 65 00 00 00 00                       "Richie\0\0\0\0"
0x20d58    00 00 00 00 04 00 00 00                             Padding + Type 0x04
0x20d60    01 00 00 00 10 00 00 00                             Index: 1, Size: 16
0x20d68    E3 81 85 E3 80 81 E3 83 B3 E3 80 82 00 00 00 00    "ぅ、ン。\0\0\0\0"
```

### Type 0x02 and 0x03 Content Classification

Type 0x02 and 0x03 entries can contain speaker names, choice options, or bytecode:

| Category | Examples | Action |
|----------|----------|--------|
| **Character Names (SPEAKERS)** | Pearl, Richie, Zara, Nesso, Edgar, Elza, パール, リッチー | KEEP - pairs with Type 0x04/0x05/0x07 dialogue |
| **Character IDs** | her01, zara01, rathL02, zk01, rich | FILTER OUT (bytecode) |
| **Other Bytecode** | bg96, bg098, suma, switch, FavZara | FILTER OUT (bytecode) |

**Note (v1.1.4)**: Type 0x03 entries can also contain speaker names in Japanese Katakana (e.g., "パール", "リッチー"). The decompiler now recognizes speaker names in both Type 0x02 and Type 0x03 entries.

### Speaker Name List

The following character names (English and Japanese) are recognized as speakers:

**English**: Pearl, Richie, Nesso, Zara, Edgar, Elza, Rath, Guillan, Arles, Henrietta

**Japanese (Katakana)**: パール, リッチー, ネッソ, ザラ, エドガー, エルザ, ラス, ギラン, アルル, ヘンリエッタ

---

## Entry Types (Dialogue Format)

| Type Value | Description | Notes |
|------------|-------------|-------|
| 1 | Standard dialogue | Most common type |
| 2 | Choice/branch | Dialogue options |
| 11 | Header/meta | Often appears as first entries |

---

## Decompilation Strategy

1. **Scan for entry headers**: Pattern match `XX00 YY00` where XX and YY are small integers
2. **Verify speaker prefix**: Check for known speaker name patterns
3. **Extract all text segments**: Find UTF-8 sequences between padding
4. **Select main dialogue**: Use longest segment as primary text
5. **Filter bytecode**: Skip known instruction patterns
6. **Format output**: Convert #n to newlines, show short labels in brackets

---

## v1.0.3 Format Discoveries

### Full STCM2L Parser - Bracketed Notes Format

The full STCM2L format parser creates entries with **bracketed notes** when multiple text segments are found within an entry boundary.

#### Format Structure

```
Main Text [note1, note2, note3, ...]
```

#### Example from File 101

**Binary storage (separate locations):**
- `いいえ` (Japanese "No") at 0x01EA18
- `select` (UI element) at 0x01EA64
- `ef_shake5` (effect code) at 0x01ECE8
- `Rain, fine...` (English narration) at 0x01EE0C

**Parser output (before filtering):**
```
Rain, fine as if it were mist, drizzles with a soft pitter-patter. [ef_shake5, select, いいえ]
```

The **longest segment** becomes the main text, and shorter segments become bracketed notes.

#### Combining Issue (v1.0.3 Fix)

When the combining logic encounters bracketed-note entries:

1. **`select` and `ef_shake5`** were NOT filtered as bytecode → treated as valid text
2. **Bracketed entries** were combined because `]` wasn't recognized as terminal punctuation
3. **Result**: `いいえselectselectef_shake5Rain, fine...` (corrupted)

**Fix applied:**
1. Added `ef_*`, `select`, `export_data` to bytecode filter patterns
2. Added bracketed-notes detection: entries ending with `]` don't combine further
3. Added `]` to terminal punctuation regex

#### Prologue Skip Dialog Example (File 101)

The game contains a prologue skip confirmation dialog:

| Binary Offset | UTF-8 Text | Meaning |
|---------------|------------|---------|
| 0x01E94C | `プロローグをスキップしますか？` | "Will you skip the prologue?" |
| 0x01E9C4 | `はい` | "Yes" (filtered by length check - 2 chars) |
| 0x01EA18 | `いいえ` | "No" (Entry 4699) |
| 0x01EA64 | `select` | UI button text (filtered) |
| 0x01ECE8 | `ef_shake5` | Effect code (filtered) |
| 0x01EE0C | `Rain, fine...` | English narration (Entry 4742) |

**After v1.0.3 fix:**
- Entry 4699: `いいえ` (clean Japanese dialogue)
- Entry 4742: `Rain, fine as if it were mist...` (separate narration entry)
- `select` and `ef_shake5` are filtered out entirely

### Legacy UTF-8 Parser Behavior

The `_parse_legacy_utf8()` function scans for valid UTF-8 strings and assigns them entry indexes based on their binary position. Nearby unrelated strings can get assigned similar indexes, which then get incorrectly combined if:
1. No terminal punctuation at end
2. Next entry starts with lowercase
3. No language mixing detection

This is why `いいえ` (No) was combined with `select`, `ef_shake5`, and English narration.

---

## Binary Structure Analysis (File 101)

### Structured Entry Format

File 101 contains dialogue entries in a structured format:

**Entry Header (12 bytes):**
```
Offset  Size    Description
------  ----    -----------
+0x00   4       Type (little-endian uint32): 0x02, 0x03, 0x04, 0x0B, 0x0C
+0x04   4       Index (little-endian uint32)
+0x08   4       Size (little-endian uint32)
+0x0C   var     UTF-8 string data (null-padded)
```

### Entry Types

| Type | Description | Example |
|------|-------------|---------|
| 0x01 | English choice options | "Yes", "No", "OK", "Cancel" (v1.1.13) |
| 0x02 | Choice options / bytecode | `はい`, `いいえ`, `switch` |
| 0x03 | Choice options / bytecode | Various short strings |
| 0x04 | Main dialogue | Full dialogue text |
| 0x0B | Dialogue / metadata | `プロローグ　孤独の狼と籠の塔` |
| 0x0C | Questions / dialogue | `プロローグをスキップしますか？`, `prologue` |

### Binary Examples

**At 0x1BDA0 (Prologue Title):**
```
Offset     Hex                              Decoded
-------    ------------------------------  -------
0x1BDA0    0b 00 00 00                     Type = 0x0B
0x1BDA4    01 00 00 00                     Index = 1
0x1BDA8    2c 00 00 00                     Size = 44 (0x2C)
0x1BDAC    e3 83 97 e3 83 ad ...           UTF-8: "プロローグ　孤独の狼と籠の塔"
```

**At 0x1E940 (Prologue Skip Question):**
```
Offset     Hex                              Decoded
-------    ------------------------------  -------
0x1E940    0c 00 00 00                     Type = 0x0C
0x1E944    01 00 00 00                     Index = 1
0x1E948    30 00 00 00                     Size = 48 (0x30)
0x1E94C    e3 83 97 e3 83 ad ...           UTF-8: "プロローグをスキップしますか？"
```

**At 0x1F4A8 and 0x1F4BC (Type 0x01 English Choice Options - v1.1.13):**
```
Offset     Hex                              Decoded
-------    ------------------------------  -------
0x1F4A8    01 00 00 00                     Type = 0x01 (English choice option)
0x1F4AC    01 00 00 00                     Index = 1
0x1F4B0    04 00 00 00                     Size = 4
0x1F4B4    59 65 73 00                     UTF-8: "Yes\0"

Offset     Hex                              Decoded
-------    ------------------------------  -------
0x1F4BC    01 00 00 00                     Type = 0x01 (English choice option)
0x1F4C0    01 00 00 00                     Index = 1
0x1F4C4    04 00 00 00                     Size = 4
0x1F4C8    4e 6f 00 00                     UTF-8: "No\0\0"
```

**Note on Type 0x01**: These entries contain English UI choice options (Yes, No, OK, Cancel, etc.). They are converted to Type 0x02 for consistency with existing choice format and grouped with Japanese choices (はい, いいえ) by the decompiler.

### Index Field Usage

The binary `Index` field groups related entries:
- Question and choices often share the same Index (e.g., Index 1)
- Most dialogue entries have Index 0 or 1
- The decompiler assigns **sequential display indices** (4218, 4233, etc.) based on UTF-8 string position for readability

### Parser Strategy

**Current approach (v1.1.0+):**
1. Scan for UTF-8 strings using `_parse_legacy_utf8()`
2. Filter out bytecode using `_is_valid_text()`
3. Combine related entries using `combine_dialogue_entries()`
4. Display uses sequential indices, not binary Index field

**Why not use structured parser:**
- Structured parser finds 417 entries (mostly bytecode with small sizes)
- UTF-8 scanner finds 74 entries after filtering, 40 after combining
- UTF-8 approach produces correct output for translators

---
