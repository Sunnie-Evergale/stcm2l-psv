# Changelog - STCM2L Decompiler

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.27] - 2026-01-01

### Fixed
- **Quote closure across Type 8/10 entries not working**: Fixed issue where unclosed quotes spanning Type 0x08/0x0A entries were not being combined
  - Root cause: Quote closure logic was only implemented in speaker combining handler (line 403-442), but entries with `#Name[X]` indicators are processed through standalone dialogue handler (line 684+)
  - Added quote closure logic to standalone dialogue handler (lines 782-804)
  - After `should_combine_entries` returns False due to terminal punctuation + capital letter, check if combined text has unclosed quote
  - If unclosed quote found, continue combining Type 0x08/0x0A/0x0C/0x0D entries until quote is closed
  - Added Type 0x08 and 0x0A to quote closure continuation list in speaker combining handler (line 410)
  - Entries with unclosed quotes now properly combine across Type 8/10/12 boundaries

### Analysis
- Binary structure investigation at offset 0x36ce8 (Entry 672 in v1.1.26, 667 in v1.1.27) confirmed Type 0x08 entry has unclosed quote: `"Here, please come and look.`
- Entry 673 (Type 0x0A) continues with: `If you're just looking, that's free.`
- Entry 674 (Type 0x0C) closes quote: `If you see anything you like, just tell me."`
- The terminal punctuation check stopped combining after Entry 672, and quote closure logic didn't exist in standalone dialogue handler
- `#Name[1]` is NOT in SPEAKER_NAMES set, so it's processed as a name indicator, not a speaker name
- Name indicator entries use look-back logic (line 686+) to find the `#Name[X]` prefix and prepend it to text
- This means these entries go through standalone dialogue handler, not speaker combining handler

### Example of Fixed Entry (File 107)
**Entry 672-674 (v1.1.26):**
```
--- Entry 672 (Type: 8) ---
Speaker: #Name[1]
Text: "Here, please come and look.

--- Entry 673 (Type: 10) ---
Text: If you're just looking, that's free.

--- Entry 674 (Type: 12) ---
Text: If you see anything you like, just tell me."
```

**Entry 667 (v1.1.27):**
```
--- Entry 667 (Type: 8) ---
Speaker: #Name[1]
Text: "Here, please come and look. If you're just looking, that's free. If you see anything you like, just tell me."
```

### Changed
- File 107: 767 entries (v1.1.26) → 755 entries (v1.1.27) = 12 entries combined due to quote closure fix

## [1.1.26] - 2026-01-01

### Fixed
- **Entries starting with `"--` wrongly combined with previous speaker**: Fixed issue where Type 0x0B entries starting with `"--` (quote-dash-dash) were being combined with the preceding speaker
  - Root cause: Binary analysis confirmed `"--` prefix at start of entry is a structural marker indicating speaker context change
  - Added check `if next_text.strip().startswith('"--'): break` in speaker combining logic
  - These entries now become standalone entries without incorrect speaker attribution

### Analysis
- Binary structure investigation at offset 0x4ee00 confirmed `"--` is part of text data, not a structural separator
- Pattern analysis of file 106 showed only ONE entry (1317) had `"--` at START with a speaker
- Other entries with `--` in middle (em dash usage like "And -- of all things") are unaffected

### Example of Fixed Entry (File 106)
**Entry 1317 (v1.1.25):**
```
--- Entry 1317 (Type: 4) ---
Speaker: Rath
Text: "--it's not there, where are you going?" I give him a very vague answer.
```

**Entry 1317 (v1.1.26) - Expected:**
```
--- Entry 1317 (Type: 4) ---
Text: "--it's not there, where are you going?" I give him a very vague answer.
```
(Standalone entry, no incorrect speaker attribution)

## [1.1.25] - 2026-01-01

### Fixed
- **Multi-entry quote closure not working**: Fixed issue where split quotes across 3+ entries were not being combined
  - Root cause: v1.1.24 quote matching logic only looked ONE entry ahead for quote closure
  - Enhanced to loop through multiple entries after terminal punctuation break
  - Now handles cases where closing quote is 2+ entries ahead
- **Type 15 (0x0F) entries not being combined**: Fixed issue where consecutive Type 0x0F entries were not being combined
  - Root cause: Type 0x0F was removed from combine lists in v1.1.22 due to "dialogue OR narration" ambiguity
  - Re-added Type 0x0F to standalone dialogue handler combine lists
  - Type 0x0F entries that follow each other are now properly combined

### Changed
- Enhanced quote matching logic to look multiple entries ahead for quote closure
- Added Type 0x0F to standalone dialogue combine lists (lines 654, 665, 705)
- Quote closure now handles Type 4/6/3/15 entries across multiple lookahead iterations

### Example of Fixed Entries (File 106)
**Entry 1057-1059 (multi-entry quote closure):**
```
v1.1.24 (incorrectly split):
--- Entry 1057 (Type: 4) ---
Speaker: Rath
Text: "Ah. I'm...

--- Entry 1058 (Type: 4) ---
Text: I woke you up.

--- Entry 1059 (Type: 3) ---
Text: My bad..."

v1.1.25 (correctly combined):
--- Entry 1057 (Type: 4) ---
Speaker: Rath
Text: "Ah. I'm... I woke you up. My bad..."
```

**Entry 1077-1078 (Type 15 combining):**
```
v1.1.24 (incorrectly split):
--- Entry 1077 (Type: 15) ---
Text: Rath had, always, through I don't know what kind of magic,

--- Entry 1078 (Type: 15) ---
Text: built a fire the night before which never stopped burning.

v1.1.25 (correctly combined):
--- Entry 1077 (Type: 15) ---
Text: Rath had, always, through I don't know what kind of magic, built a fire the night before which never stopped burning.
```

## [1.1.24] - 2026-01-01

### Fixed
- **Split quotes not being combined across Type 12/13 narration entries**: Fixed issue where dialogue split across multiple entries by Type 12/13 narration was not being properly combined
  - Root cause: Terminal punctuation check broke combining before checking if Type 12/13 entries followed
  - After terminal punctuation, now continues combining if next entry is Type 12/13
  - Also continues combining if next Type 4/6 entry closes an unclosed quote (odd quote count detection)
  - File 106: Entry count decreased from 1358 (v1.1.23) to 1349 (v1.1.24) due to proper combining

### Changed
- Added quote matching logic to detect unclosed quotes after terminal punctuation
- Type 12/13 entries (continuation narration) now combined with dialogue even after periods
- Prevents fragmentation of multi-part dialogue sentences

### Example of Fixed Entry (File 106, entries 879-881)
**v1.1.23 (incorrectly split):**
```
--- Entry 879 (Type: 4) ---
Speaker: Rath
Text:
"It's a bad feeling.

--- Entry 880 (Type: 12) ---
Text:
When I'm touched it's definitely a bad feeling.

--- Entry 881 (Type: 4) ---
Text:
I feel weak."
```

**v1.1.24 (correctly combined):**
```
--- Entry 876 (Type: 4) ---
Speaker: Rath
Text:
"It's a bad feeling. When I'm touched it's definitely a bad feeling. I feel weak."
```

## [1.1.23] - 2026-01-01

### Fixed
- **ASCII period missing from terminal punctuation check**: Fixed critical bug where ASCII period (`.`) was not included in the terminal punctuation list for speaker combining logic
  - Root cause: Line 422 only checked for `!`, `?`, `。`, `！`, `？` but NOT `.`
  - This caused complete sentences ending with periods to continue combining with subsequent entries
  - Result: Narration starting with capital letters was incorrectly combined with dialogue and given speaker labels
  - Added `.` to the terminal punctuation list at line 423

### Changed
- Added ASCII period (`.`) to terminal punctuation check in speaker combining logic
- File 106: Entries now correctly split at sentence boundaries (e.g., entry 966 vs 967 vs 968)

### Example of Fixed Entry (File 106)
**v1.1.21 (incorrectly combined - narration has speaker label):**
```
--- Entry 954 (Type: 4) ---
Speaker: Rath
Text:
"...Shut up. I'm fine alone." When Rath's blue eyes emit something gloomy in the dark, I unintentionally gulp. My heart trembles.
```

**v1.1.23 (correctly separated - narration has no speaker):**
```
--- Entry 966 (Type: 4) ---
Speaker: Rath
Text:
"...Shut up.

--- Entry 967 (Type: 5) ---
Text:
I'm fine alone."

--- Entry 968 (Type: 15) ---
Text:
When Rath's blue eyes emit something gloomy in the dark,
```

### Research Summary
Conducted comprehensive research on three existing STCM2L repositories:
- xyzz/hkki (C++ - Hakkuouki DS game)
- kubo25/Diabolik-Lovers-STCM2L-Editor (C#)
- Yggdrasill-Moe/Helheim (Python - Chinese project)

**Key Findings:**
- Other repositories use different file format (bytecode CODE_START_ vs pre-parsed dialogue format)
- Other repos use opcodes (D2, D4, E7) vs our Type field (0x01-0x12) - different systems
- Other repos use simpler sequential collection approach (no complex combining logic)
- Our Type 0x07/0x0F narration detection is unique and valuable (kept in implementation)
- Parameter filter `param >> 30 == 0` from Helheim repo not applicable to our format

**Conclusion:**
Our implementation uses a different file format than other repositories. The combining logic complexity is necessary for our format's specific challenges. The ASCII period bug was the root cause of many incorrectly combined entries.

## [1.1.22] - 2026-01-01

### Fixed
- **Narration being combined with dialogue**: Fixed issue where Type 0x0F narration entries were being incorrectly combined with dialogue entries and given speaker labels
  - Root cause: Type 0x0F was included in the Type 0x02/0x03 speaker combining list
  - Type 0x0F can be dialogue continuation OR narration, similar to Type 0x07
  - Removed Type 0x0F from the Type 0x02/0x03 combine list (line 414)
  - Type 0x0F entries are now processed independently and will not be labeled with speaker names
  - Also added capital letter check to prevent combining dialogue with narration when text ends with sentence punctuation
```

**Finding:** Type 0x0F, like Type 0x07, can contain either dialogue continuation OR narration. By including it in the Type 0x02/0x03 combine list, narration text was being labeled with speaker names. The fix removes Type 0x0F from the combine list, allowing it to be processed independently. The additional capital letter check prevents combining entries when a complete sentence is followed by text starting with a capital letter (indicating a new sentence or narration).

## [1.1.21] - 2025-12-31

### Fixed
- **Type 0x07 narration being incorrectly combined with speaker labels**: Fixed issue where Type 0x07 narration entries were being combined with speaker labels from preceding Type 0x02/0x03 speaker entries
  - Root cause: Type 0x07 was included in the Type 0x02/0x03 speaker combining list, causing narration to be labeled with speaker names
  - Type 0x07 entries can be dialogue OR narration, and have separate logic (lines 536-623) to determine which
  - By removing Type 0x07 from the Type 0x02/0x03 combine list, Type 0x07 entries are now processed independently
  - The Type 0x07 logic correctly identifies narration by looking backward and stopping at dialogue entries (Type 0x04, 0x05, 0x06, etc.)

### Changed
- Removed Type 0x07 from Type 0x02/0x03 speaker combining list
- Type 0x07 entries now processed independently by their own logic to determine dialogue vs narration
- File 106: 1297 entries → 1292 entries (some incorrectly combined entries are now separate)

### Example of Fixed Entry (File 106, Entry 947-948)
**v1.1.20 (incorrectly combined - narration has speaker label):**
```
--- Entry 954 (Type: 4) ---
Speaker: Rath
Text:
"...Ha...ha..." His breathing is ragged.
```

**v1.1.21 (correctly separated - narration has no speaker):**
```
--- Entry 947 (Type: 4) ---
Speaker: Rath
Text:
"...Ha...ha..."

--- Entry 948 (Type: 7) ---
Text:
His breathing is ragged. 食い破った喉、だくだくと溢れる鮮血を
```

**Finding:** Type 0x07 entries can be dialogue continuation OR narration. The Type 0x07 logic (lines 536-623) determines this by looking backward for a speaker. If it finds a Type 0x04/0x05/0x06/0x07/0x0D/0x0E entry before finding a Type 0x02/0x03 speaker, it treats the Type 0x07 as narration (no speaker). By allowing Type 0x02/0x03 to combine Type 0x07 entries, this logic was bypassed.

## [1.1.20] - 2025-12-31

### Fixed
- **False positive bytecode pattern filtering normal English text**: Fixed issue where normal English text containing the word "sure" was being filtered out as bytecode
  - Root cause: Bytecode pattern `\bsure\d*` was matching the English word "sure" (requires zero or more digits)
  - File 106: Entry 1014/1015 was truncated - missing "he's checking to make sure I'm asleep."
  - Binary analysis confirmed Type 0x0A entry exists at offset 0x49350 with text "he's checking to make sure I'm asleep."
  - Changed pattern to `\bsure\d+` (requires one or more digits) to prevent false positives on normal English text
  - Also improved merging logic to track entry offsets for better handling of duplicate indices

### Changed
- Fixed bytecode pattern `\bsure\d*` → `\bsure\d+` to require at least one digit after "sure"
- Added offset tracking to compact and padded format parsers (stored in `offset` field)
- Improved merging logic to sort entries by (index, offset) instead of just index
- File 106: 1287 entries → 1297 entries (+10 entries recovered, including the Type 0x0A at 0x49350)

### Example of Recovered Entry (File 106, Entry 1015)
**v1.1.19 (truncated - missing Type 0x0A):**
```
--- Entry 1014 (Type: 13) ---
Speaker: #Name[1]
Text:
#Name[1]
In time, Rath stands up in a manner that's as if

--- Entry 1015 (Type: 6) ---
Speaker: #Name[1]
Text:
#Name[1]
(...What's going on?)
```

**v1.1.20 (Type 0x0A included and combined):**
```
--- Entry 1015 (Type: 13) ---
Speaker: #Name[1]
Text:
#Name[1]
In time, Rath stands up in a manner that's as if he's checking to make sure I'm asleep.  ← NEW!

--- Entry 1016 (Type: 6) ---
Speaker: #Name[1]
Text:
#Name[1]
(...What's going on?)
```

**Finding:** The bytecode pattern `\bsure\d*` was meant to match bytecode variables like `sure1`, `sure2` but was also matching the English word "sure" in normal dialogue. The `\d*` quantifier matches zero or more digits, so "sure" alone was a match. Changing to `\d+` requires at least one digit.

## [1.1.19] - 2025-12-30

### Fixed
- **Type 0x11 entry type not supported**: Fixed issue where Type 0x11 entries were being completely filtered out
  - Root cause: Type 0x11 was not included in any valid type lists
  - File 106: Entry 920 was truncated - missing "and then it was very gentle, and then your mouth cracked a smile."
  - Binary analysis confirmed Type 0x11 exists at offset 0x47410 with dialogue text
  - Added Type 0x11 to all valid type lists and combining logic

### Changed
- Added Type 0x11 to valid type lists in both compact and padded format parsers
- Added Type 0x11 to all dialogue combining logic (4 locations)
- File 106: 1281 entries → 1296 entries (+15 Type 0x11 entries now included)

### Example of Recovered Entry (File 106, Entry 920)
**v1.1.18 (truncated - missing Type 0x11):**
```
--- Entry 920 (Type: 11) ---
Text:
Your expression was like you were amazed,

--- Entry 921 (Type: 4) ---
Speaker: Rath
Text:
"....You saw wrong."
```

**v1.1.18 (Type 0x11 included):**
```
--- Entry 920 (Type: 11) ---
Text:
Your expression was like you were amazed,

--- Entry 921 (Type: 17) ---
Text:
and then it was very gentle, and then your mouth cracked a smile.  ← NEW!

--- Entry 922 (Type: 4) ---
Speaker: Rath
Text:
"....You saw wrong."
```

**Finding:** Type 0x11 is a dialogue continuation type similar to Type 0x0D, 0x0E, 0x0F, 0x10. It was missed when adding those types in previous versions.

## [1.1.18] - 2025-12-30

### Fixed
- **Type 0x10 entry type not supported**: Fixed issue where Type 0x10 entries were being completely filtered out
  - Root cause: Type 0x10 was not included in any valid type lists, despite Type 0x0D, 0x0E, 0x0F being added in previous versions
  - Type 0x10 entries have a **placeholder size field (0x4000)** instead of actual text size, requiring special handling
  - Without special size handling, Type 0x10 would fail the `entry_size > 10000` validation and cause parsing misalignment
  - Implemented special size calculation for Type 0x10: scans for null terminator instead of using declared size

### Changed
- Added Type 0x10 to valid type lists in both compact and padded format parsers
- Added Type 0x10 to all dialogue combining logic (4 locations)
- Implemented special size handling for Type 0x10: calculates actual size by finding null terminator (max 500 bytes)
- File 106: 1201 entries → 1281 entries (+80), 62 Type 0x10 entries now included

### Example of Recovered Entry (File 106, Entry 950)
**v1.1.17 (missing Type 0x10):**
```
--- Entry 889 (Type: 14) ---
Text: 食い破った喉、だくだくと溢れる鮮血を

--- Entry 890 (Type: 3) ---
Text: Little girl
```

**v1.1.18 (Type 0x10 included):**
```
--- Entry 949 (Type: 14) ---
Text: 食い破った喉、だくだくと溢れる鮮血を

--- Entry 950 (Type: 16) ---
Text: 啜り、傷口にむしゃぶりついて喉を鳴らす。  ← NEW!

--- Entry 951 (Type: 3) ---
Text: Little girl
```

**Finding:** Type 0x10 is a dialogue continuation type similar to Type 0x0D, 0x0E, 0x0F, but with a special size field format that requires custom parsing logic.

## [1.1.17] - 2025-12-29

### Fixed
- **Language mixing detection for Japanese text with romaji**: Fixed issue where Japanese text containing romaji (alphabetic characters) was incorrectly combined with English entries
  - Root cause: Language mixing check only tested `if (prev_has_english and curr_has_japanese and not curr_has_english)` but Japanese text like `"痛い……！"` contains English letters (i-t-a-i = 7 letters), making `curr_has_english = True`, so `not curr_has_english = False`, causing the check to fail
  - File 106: Entry 773 was combining `"...Ha...ha..." His breathing is ragged.` with `食い破った喉、だくだくと溢れる鮮血を` and `痛い……！`
  - Now properly separated into distinct entries
  - Added check: If current text has both Japanese AND English (romaji) → don't combine with either pure Japanese or pure English entries

### Changed
- `should_combine_entries()`: Added romaji mixing check (lines 180-184)
  - If `curr_has_japanese and curr_has_english` → return False (don't combine)
- Type 0x02/0x03 speaker combining loop: Added romaji mixing check (lines 406-423)
  - Same logic applied to speaker combining to prevent mixing languages
- File 106: 1175 entries → 1201 entries (language-separated entries no longer combined)

### Binary Analysis (File 106, Entry 773)

**Original Incorrect Output (v1.1.16):**
```
--- Entry 773 (Type: 4) ---
Speaker: Rath
Text:
"...Ha...ha..." His breathing is ragged. 食い破った喉、だくだくと溢れる鮮血を 痛い……！ Little girl "That hurts...!
```

**Correct Output (v1.1.17):**
```
--- Entry 773 (Type: 4) ---
Speaker: Rath
Text:
"...Ha...ha..." His breathing is ragged.

--- Entry 774 (Type: 14) ---
Text:
食い破った喉、だくだくと溢れる鮮血を

--- Entry 775 (Type: 10) ---
Speaker: #Name[1]
Text:
痛い……！
```

**Finding:** Japanese text with romaji (like `"痛い……！"`) was being detected as having English content (7 alphabetic characters: i-t-a-i), causing the language mixing detection to fail. The fix adds an explicit check for text that contains BOTH Japanese AND English characters, treating it as a language mixing case that should not be combined.

## [1.1.16] - 2025-12-29

### Fixed
- **Horizontal ellipsis not treated as terminal punctuation**: Fixed issue where entries ending with `…` (U+2026 HORIZONTAL ELLIPSIS) were being incorrectly combined with subsequent entries
  - Root cause: `should_combine_entries()` function's terminal punctuation regex didn't include `…`
  - File 101: "Mejojo…. Auger… I'll kill you both…" now stops combining at ellipsis (was incorrectly combining with "Unpleantly a leaf...")
  - Added `…` to terminal punctuation regex: `[。！？\.!?\"』）\]…]`
- **File path handling in main() function**: Fixed issue where file paths ending with `.txt` caused directory creation errors
  - Root cause: `main()` function tried to create directory at `extract/decompiled_v1.1.16/101.txt` instead of parent directory only
  - Solution: Added check for `.txt` extension to only create parent directory

### Added
- **Type 0x0F entry type support**: Added support for Type 0x0F entries (dialogue continuation)
  - Type 0x0F entries contain dialogue continuation text that was being skipped
  - Added to all valid type lists and combining logic
  - File 101: Type 0x0F entries like "his clothing. Unperturbed, the young man..." now properly parsed

### Format Updates
- Added entry type 0x0F to valid types list in `_parse_padded_format()` (line 950)
- Added entry type 0x0F to valid types list in `_parse_compact_format()` (line 1051)
- Added Type 0x0F to combining logic in multiple locations (lines 377, 537, 583, 594, 631)
- Horizontal ellipsis `…` (U+2026) added to terminal punctuation list (line 186)

### Test Results
- Entry 17 in file 101 now correctly splits into separate entries instead of combining across ellipsis
- Type 0x0F entries now properly parsed and combined with dialogue
- 119/119 SCRIPT files successfully processed

## [1.1.15] - 2025-12-28

### Fixed
- **Type 0x07 + Type 0x05 not combining**: Fixed issue where Type 0x07 dialogue continuation entries were not combined with Type 0x05/0x06/0x08/0x09/0x0A entries
  - Root cause: Type 0x07 handler only combined with other Type 0x07 entries with the same index
  - File 103: "When the party is over I'll give you a massage." now complete (Type 0x07 + Type 0x05 combined)
  - Before: "When the party is over I'll" was truncated, missing "give you a massage."
  - Modified Type 0x07 handler to combine with ALL dialogue continuation types (0x03-0x0E except 0x12)
- **Type 0x0D and 0x0E not supported**: Fixed issue where Type 0x0D and 0x0E dialogue continuation entries were not being parsed or combined
  - Root cause: Type 0x0D and 0x0E were not in the valid types list or combining types list
  - File 103: "Before the guests arrive, you three will have to change, along with other preparations. Take that into account..." now complete (Type 0x09 + Type 0x0D + Type 0x0E combined)
  - Before: "Before the guests arrive, you three" was truncated, missing continuation text
  - Added Type 0x0D and 0x0E to parser validation and all combining logic

### Added
- **Type 0x0D entry type support**: Added support for Type 0x0D entries (dialogue continuation)
- **Type 0x0E entry type support**: Added support for Type 0x0E entries (dialogue continuation)
- **Type 0x07 enhanced combining**: Type 0x07 entries now combine with all dialogue continuation types (0x03-0x0E except 0x12)
  - Type 0x07 + Type 0x07 still requires same index (preserves original behavior)
  - Type 0x07 + Type 0x05/0x06/etc. combines regardless of index (new behavior)

## [1.1.14] - 2025-12-28

### Fixed
- **Type 0x03 dialogue continuation not combined**: Fixed issue where Type 0x03 entries containing dialogue continuation were not being combined
  - Root cause: Type 0x03 was not in the combining types list
  - File 103: "Even so, you are a Lobeira." now complete (Type 0x05 + Type 0x03 combined)
  - Before: "Even so, you are" was truncated, missing "a Lobeira."
  - Added Type 0x03 to combining types in speaker look-ahead (line 376) and main combining (line 596)
- **Type 0x03 name indicators in text**: Fixed issue where Type 0x03 "#Name[X]" entries appeared in output text
  - Root cause: Type 0x03 entries that are name indicators were not being filtered
  - Solution: Added check to skip Type 0x03 name indicators (line 433-436)
- **Dialogue entries not finding name indicators**: Fixed issue where dialogue entries after Type 0x02 speakers couldn't find name indicators
  - Root cause: Look-back logic stopped at Type 0x02 speaker entries
  - Solution: Modified look-back to continue past Type 0x02 speakers when no name indicator found yet (line 587-590)
- **Type 0x03 entries incorrectly filtered as bytecode**: Fixed issue where valid Type 0x03 dialogue continuation was filtered
  - Root cause: Type 0x03 non-speaker entries were being unconditionally skipped as bytecode
  - Solution: Added bytecode check before skipping (line 432-450)

### Added
- **Type 0x03 to combining types**: Type 0x03 entries can now combine with Type 0x04/0x05/0x06/0x07/0x08/0x09/0x0A/0x0B/0x0C dialogue entries
- **Type 0x03 bytecode check**: Type 0x03 entries that are not name indicators now pass bytecode validation if they're valid text
- **Type 0x03 name indicator handling**: Type 0x03 "#Name[X]" entries are now properly skipped but findable by look-back logic

## [1.1.13] - 2025-12-28

### Fixed
- **Type 0x01 entries not parsed**: Fixed issue where English UI choice options (Yes, No, OK, etc.) were not being extracted
  - Root cause: Type 0x01 is a previously undocumented entry type containing English choice options
  - File 101: "Will you skip the prologue?" now shows [4 options: はい / いいえ / Yes / No]
  - Before: Only Japanese choices (はい / いいえ) were shown; English choices (Yes / No) were missing
- **Compact format parser boundary issue**: Fixed issue where entries at file end were not parsed
  - Root cause: Loop condition `pos < len(data) - 16` excluded entries at exactly file_size - 16
  - Solution: Changed to `pos + 12 <= len(data)` to allow processing entries at file boundary
  - "No" entry at 0x1F4BC (file end - 16 bytes) was not being parsed
- **Short English words filtered as bytecode**: Fixed issue where 2-letter English words like "No" were filtered
  - Root cause: `_is_valid_text()` required MORE THAN 2 English letters (`> 2`)
  - Solution: Changed to `>= 2` to allow "No" and other 2-letter words

### Added
- **Type 0x01 entry type support**: Added support for Type 0x01 entries (English UI choice options)
  - Type 0x01 contains English choice words: Yes, No, OK, Cancel, Accept, Decline, Close
  - Converted to Type 0x02 for consistency with existing choice format
  - Only known choice words are converted; other Type 0x01 entries filtered as garbage
- **English choice words to bytecode filter**: Added exception in `is_bytecode()` for English choice words
- **English choice words to text validation**: Added exception in `_is_valid_text()` for English choice words

### Changed
- Added Type 0x01 to valid types in `_parse_padded_format()` (line 869)
- Added Type 0x01 to combining type list in `_parse_padded_format()` (line 931)
- Added Type 0x01 to valid types in `_parse_compact_format()` (line 966)
- Added Type 0x01 handler in `combine_dialogue_entries()` (lines 451-470)
- Added Type 0x01 to dialogue combining exclude list (lines 357, 571)
- Updated `is_choice_candidate()` to recognize Type 0x02 entries with English choice words
- Compact format parser loop condition changed from `pos < len(data) - 16` to `pos + 12 <= len(data)` (line 978)
- `_is_valid_text()` English threshold changed from `> 2` to `>= 2` (line 1154)

### Binary Analysis (File 101)

**Type 0x01 Entry Examples:**
| Offset | Type | Index | Size | Data |
|--------|------|-------|------|------|
| 0x1F4A8 | 0x01 | 1 | 4 | "Yes" (English choice) |
| 0x1F4BC | 0x01 | 1 | 4 | "No" (English choice) |

**Entry Structure:**
```
Offset  Size    Description
------  ----    -----------
+0x00   4       Type (little-endian uint32): 0x01
+0x04   4       Index (little-endian uint32)
+0x08   4       Size (little-endian uint32)
+0x0C   var     UTF-8 string data (null-terminated)
```

**Finding**: Type 0x01 is a previously undocumented entry type containing English UI choice options. The entries use compact format (no padding prefix) and are stored at the CODE_START_ section in full STCM2L format files.

### Entry Type Clarification (Updated)

| Type | Description | Example Content | Action |
|------|-------------|-----------------|--------|
| **0x01** | **English choice options** | **Yes, No, OK, Cancel** | **Convert to 0x02, group as choices** |
| 0x02 | Speaker Name / Bytecode | Pearl, Richie, bg96, suma | Speaker names: KEEP, Bytecode: FILTER |
| 0x03 | Speaker Name / Choice Options | Pearl, パール, はい | Speaker names: KEEP, Bytecode: FILTER |

## [1.1.12] - 2025-12-28

### Fixed
- **Type 0x07 entries not combined with same index**: Added combining logic for Type 0x07 entries with the same index
  - Entry 987: "(I think it's cute though." + "He's a bunny, after all.)" → "(I think it's cute though. He's a bunny, after all.)"
  - Entry 988: "As I thought this, a small chuckle" + "slipped out unconciously." → "As I thought this, a small chuckle slipped out unconciously."
- **Type 0x09 entries not parsed**: Type 0x09 dialogue entries were not in valid types list
  - Root cause: Type 0x09 was missing from all valid type and combining type lists
  - Type 0x09 is a dialogue type similar to Type 0x04/0x05/0x06

### Changed
- `combine_dialogue_entries()`: Added Type 0x07 combining logic with same index (lines 459-487)
- Added Type 0x09 to all valid type lists (lines 373, 547, 836, 915, 982)
- Added Type 0x09 to combining type lists (lines 374, 549)
- File 103: 1750 entries → 1908 entries (Type 0x07/0x09 entries now parsed and combined)

### Binary Analysis (File 103)

**Type 0x07 Combining Example:**
| Offset | Type | Index | Size | Data |
|--------|------|-------|------|------|
| 0x813CC | 0x07 | 1 | 28 | "(I think it's cute though." |
| 0x813FC | 0x07 | 1 | 28 | "He's a bunny, after all.)" |

**Type 0x09 Entry Example:**
| Offset | Type | Index | Size | Data |
|--------|------|-------|------|------|
| 0x81490 | 0x09 | 1 | 36 | "As I thought this, a small chuckle" |
| 0x814C0 | 0x07 | 1 | 28 | "slipped out unconciously." |

**Finding**: Type 0x07 entries with the same index should be combined. Type 0x09 is a dialogue continuation type that should be included in parsing and combining.

## [1.1.11] - 2025-12-28

### Fixed
- **Type 0x07 and Type 0x08 entries not combined**: Fixed issue where Type 0x07 and Type 0x08 dialogue continuation entries were excluded from combining logic
  - Entry 1095: "Please participate in my" → "Please participate in my Lady's walk."
  - Entry 1107: "This time, they had the unusual reward" → "This time, they had the unusual reward of going for a walk with me."

### Changed
- `combine_dialogue_entries()`: Added Type 0x07, 0x08 to combining logic (lines 351, 479, 516)
- `_parse_padded_format()`: Added Type 0x08 to valid entry types (line 836)
- `_parse_padded_format()`: Added Type 0x08 to skip-padding type list (line 896)
- `_parse_compact_format()`: Added Type 0x08 to valid entry types (line 929)
- File 103: 1740 entries → 1750 entries (Type 0x07/0x08 entries now combined)

### Binary Analysis (File 103)

**Type 0x07 Entry Example:**
| Offset | Pattern | Type | Data |
|--------|---------|------|------|
| 0x868B0 | 00 00 00 00 00 00 00 00 | (8 null bytes) | Padding |
| 0x868B8 | 07 00 00 00 | 0x07 | Type |
| 0x868BC | 01 00 00 00 | 1 | Index |
| 0x868C0 | 1C 00 00 00 | 28 | Size |
| 0x868C4 | "Please participate in my" | - | Data |
| 0x868E0 | 04 00 00 00 | 0x04 | Type |
| 0x868E4 | 01 00 00 00 | 1 | Index |
| 0x868E8 | 10 00 00 00 | 16 | Size |
| 0x868EC | "Lady's walk." | - | Data |

**Type 0x08 Entry Example:**
| Offset | Type | Index | Size | Data |
|--------|------|-------|------|------|
| 0x86E90 | 0x08 | 1 | 32 | "of going for a walk with" |

**Finding**: Type 0x07 and Type 0x08 are dialogue continuation types that should be combined with other dialogue entries (0x04, 0x05, 0x06, 0x0A, 0x0B, 0x0C) when they share the same index.

## [1.1.10] - 2025-12-28

### Fixed
- **Type 0x0A entries with 8-null-byte padding not parsed**: Fixed issue where Type 0x0A dialogue entries with 8 null bytes of padding were being skipped
  - Root cause: Padded format parser only handled 4-byte padding, but some Type 0x0A entries have 8-byte padding
  - This caused dialogue truncation: "If I missed this chance, I may never be able" (missing "to go for a walk after it had rained.")
  - Solution: Updated parser to detect both 4-byte and 8-byte padding patterns
- **Skip-padding logic bug**: Fixed incorrect offset calculation when 8-byte padding was detected in skip-padding logic (line 890)
- **Bytecode detection false positives**: Increased bytecode threshold from 60% to 85% to avoid misclassifying English dialogue with short words

### Changed
- `_parse_padded_format()`: Added 8-byte padding detection with variable `padding_offset` (lines 847-853)
- `_parse_padded_format()`: Fixed skip-padding logic to use correct offset for `next_size` (line 890)
- `is_bytecode()`: Increased threshold from 0.6 to 0.85 to reduce false positives on English dialogue (line 132)
- `combine_dialogue_entries()`: Skip bytecode check for Type 0x0A entries (line 535)
- File 103: 1709 entries → 1740 entries (Type 0x0A entries with 8-byte padding now parsed)

### Binary Analysis (File 103)

**Type 0x0A Entry with 8-Byte Padding:**
| Offset | Pattern | Type | Data |
|--------|---------|------|------|
| 0x85F84 | 00 00 00 00 00 00 00 00 | (8 null bytes) | Padding |
| 0x85F8C | 0A 00 00 00 | 0x0A | Type |
| 0x85F90 | 01 00 00 00 | 1 | Index |
| 0x85F94 | 28 00 00 00 | 40 | Size |
| 0x85F98 | "to go for a walk after it had rained." | - | Data |

**Finding**: Some Type 0x0A entries have 8 null bytes of padding instead of 4. The parser now handles both patterns:
- 4-byte padding: `00 00 00 00 [Type] [Index] [Size] [Data]`
- 8-byte padding: `00 00 00 00 00 00 00 00 [Type] [Index] [Size] [Data]`

## [1.1.9] - 2025-12-28

### Fixed
- **Type 0x0A entries not parsed**: Fixed issue where Type 0x0A dialogue entries were being skipped
  - Root cause: Type 0x0A was not included in the valid entry types list in both parsers
  - This caused dialogue truncation: "even though Zara told you not to!" (missing "Because, you got all dirty last time,")
  - Solution: Added 0x0A to all valid type lists and combining logic

### Changed
- `_parse_padded_format()`: Added 0x0A, 0x06, 0x12 to valid entry types (line 824)
- `_parse_compact_format()`: Added 0x0A, 0x12 to valid entry types (line 903)
- `combine_dialogue_entries()`: Added 0x0A to type checks (lines 351, 478, 516)
- `_parse_padded_format()`: Added 0x06, 0x0A to combining logic (line 870)
- File 103: 1649 entries → 1977 entries (Type 0x0A entries now parsed)

### Binary Analysis (File 103)

**Type 0x0A Dialogue Example:**
| Offset | Type | Index | Size | Data |
|--------|------|-------|------|------|
| 0x7F964 | **0x0A** | 1 | 40 | "Because, you got all dirty last time," |
| 0x7F998 | 0x05 | 1 | 20 | "even though Zara " |
| 0x7F9C0 | 0x05 | 1 | 20 | "told you not to!" |

**Finding**: Type 0x0A is a main dialogue entry type (similar to Type 0x04). All three entries have Index 1 and are combined into "Because, you got all dirty last time, even though Zara told you not to!"

### Entry Type Clarification (Updated)

| Type | Description | Has Speaker? | Should Combine? |
|------|-------------|--------------|-----------------|
| 0x02, 0x03 | Speaker names | N/A | N/A |
| 0x04 | Main dialogue | YES (from 0x02) | YES (with same speaker) |
| 0x05 | Dialogue continuation | YES (from 0x02) | YES (with same speaker) |
| 0x06 | Dialogue continuation | YES (from 0x02) | YES (with same speaker) |
| **0x0A** | **Main dialogue** | **YES (from 0x02)** | **YES (with same speaker)** |
| 0x07 | Dialogue OR Narration continuation | Only if paired with 0x02 | Only if paired with 0x02 |
| 0x0B, 0x0C | Questions / dialogue | Needs investigation | Needs investigation |
| 0x12 | Narration | NO | NO |

## [1.1.8] - 2025-12-28

### Fixed
- **Critical merge logic bug**: Fixed issue where Type 0x06 entries were being lost after merge
  - Root cause: The merge logic in `decompile_full_format()` was REPLACING entries with the same binary index
  - Since all entries have Index 1, only the last entry of each type was kept
  - This caused all but the last Type 0x06 entry to be lost (251 found → 0 remaining after merge)
  - Solution: Rewrote merge logic to APPEND entries instead of REPLACING them
- **Missing spaces in combined dialogue**: Fixed issue where combined dialogue parts had no spacing
  - Entry 831: "It makes a really funnycrumpling sound." → "It makes a really funny crumpling sound."
  - Root cause: General combining logic just concatenated text without spacing
  - Solution: Added spacing logic (same as Type 0x02 speaker combining) to add space between parts

### Changed
- `decompile_full_format()`: Fixed merge logic to APPEND entries instead of REPLACING (lines 1070-1088)
  - All compact entries are now preserved, even when they share the same binary index
  - This fixes the critical data loss bug that was affecting Type 0x06 entries
- `combine_dialogue_entries()`: Added spacing logic for general dialogue combining (line 543-546)
  - When combining dialogue parts, adds space if previous part doesn't end with space or newline
- `_parse_compact_format()`: Added Type 0x06 to valid entry types (line 903)
  - Type 0x06 is a dialogue continuation type similar to Type 0x05
- File 103: 1471 entries → 1649 entries (Type 0x06 entries now preserved and properly combined)

### Binary Analysis (File 103)

**Type 0x06 Dialogue Example:**
| Offset | Type | Index | Size | Data |
|--------|------|-------|------|------|
| 0x7F7FC | 0x06 | 1 | 24 | "It makes a really funny" |
| 0x7F824 | 0x05 | 1 | 20 | "crumpling sound." |

**Finding**: Type 0x06 entries are dialogue continuation entries similar to Type 0x05. Both have Index 1 and should be combined with proper spacing into "It makes a really funny crumpling sound."

### Entry Type Clarification

| Type | Description | Has Speaker? | Should Combine? |
|------|-------------|--------------|-----------------|
| 0x02, 0x03 | Speaker names | N/A | N/A |
| 0x04 | Main dialogue | YES (from 0x02) | YES (with same speaker) |
| 0x05 | Dialogue continuation | YES (from 0x02) | YES (with same speaker) |
| 0x06 | **Dialogue continuation** | **YES (from 0x02)** | **YES (with same speaker)** |
| 0x07 | **Dialogue OR Narration continuation** | **Only if paired with 0x02** | **Only if paired with 0x02** |
| 0x0B, 0x0C | Questions / dialogue | Needs investigation | Needs investigation |
| 0x12 | **Narration** | **NO** | **NO** |

## [1.1.7] - 2025-12-28

### Fixed
- **Narration incorrectly combined with dialogue**: Fixed issue where Type 0x07 and Type 0x12 entries were being incorrectly combined
  - Root cause: Type 0x07 entries can be either dialogue continuation OR narration continuation depending on context
  - Type 0x07 entries following Type 0x02/0x03 speakers are dialogue continuation
  - Type 0x07 entries NOT following speakers are narration continuation and should NOT be combined
  - Type 0x12 entries are pure narration and should NEVER have speakers or be combined
  - Solution: Added separate handlers for Type 0x12 (narration) and Type 0x07 (dialogue/narration detection)

### Changed
- `combine_dialogue_entries()`: Added Type 0x12 narration handler (lines 410-425)
  - Type 0x12 entries are now processed as standalone narration with NO speakers
  - Type 0x12 entries are excluded from all dialogue combining logic
- `combine_dialogue_entries()`: Added Type 0x07 dialogue/narration handler (lines 427-475)
  - Type 0x07 entries now look backward for preceding Type 0x02/0x03 speaker
  - If speaker found: dialogue continuation with speaker assigned
  - If no speaker found: narration continuation, NO speaker assigned
- `combine_dialogue_entries()`: Type 0x04/0x05 handler now excludes Type 0x07, 0x12 (line 478)
- `combine_dialogue_entries()`: General dialogue combining now only combines Type 0x04/0x05 (line 516)
- `combine_dialogue_entries()`: Type 0x02/0x03 speaker combining now only combines Type 0x04/0x05 (line 351)
- File 103: 1105 entries → 1471 entries (narration now properly separated from dialogue)

### Entry Type Clarification

| Type | Description | Has Speaker? | Should Combine? |
|------|-------------|--------------|-----------------|
| 0x02, 0x03 | Speaker names | N/A | N/A |
| 0x04 | Main dialogue | YES (from 0x02) | YES (with same speaker) |
| 0x05 | Dialogue continuation | YES (from 0x02) | YES (with same speaker) |
| 0x07 | **Dialogue OR Narration continuation** | **Only if paired with 0x02** | **Only if paired with 0x02** |
| 0x0B, 0x0C | Questions / dialogue | Needs investigation | Needs investigation |
| 0x12 | **Narration** | **NO** | **NO** |

### Binary Analysis (File 103)

**Type 12 Narration Example:**
| Offset | Type | Index | Size | Data |
|--------|------|-------|------|------|
| 0x1D558 | 0x12 | 1 | 12 | "（……ふふ、なんだか懐かしい）" (Thought in parentheses) |

**Type 7 Narration Example:**
| Offset | Type | Index | Size | Data |
|--------|------|-------|------|------|
| 0x1E91C | 0x07 | 1 | 12 | "うかがってみる。" (Narration continuation) |

**Type 7 Dialogue Example:**
| Offset | Type | Index | Size | Data |
|--------|------|-------|------|------|
| 0x94768 | 0x02 | 1 | 8 | "Zara" (Speaker) |
| 0x8A0B8 | 0x07 | 1 | 28 | "lets go outside right now!" (Dialogue continuation) |

**Finding**: Type 0x07 entries are context-dependent. When following a Type 0x02/0x03 speaker, they are dialogue continuation. When NOT following a speaker (or following Type 12), they are narration continuation.

### Known Issues
- Type 0x0B and 0x0C entries may also need special handling (currently included in general dialogue combining)
- Some Type 0x07 entries may still be incorrectly classified if the speaker pattern is not recognized

## [1.1.6] - 2025-12-28

### Fixed
- **Over-combining dialogues**: Fixed issue where unrelated dialogue fragments were incorrectly combined into word salad
  - Root cause: Type 0x02/0x03 speaker handling was combining ALL consecutive dialogue entries without stopping at speaker changes or sentence boundaries
  - Solution: Added terminal punctuation check to stop combining at '!', '?', '。', '！', '？'

### Changed
- `combine_dialogue_entries()`: Type 0x02/0x03 speakers now combine consecutive dialogue entries UNTIL:
  - Terminal punctuation is reached ('!', '?', '。', '！', '？')
  - Another Type 0x02/0x03 speaker entry is encountered
  - A #Name[X] indicator is found
  - A non-dialogue type is encountered
- `combine_dialogue_entries()`: Dialogue parts are now joined with proper spacing
- File 103: 1014 entries → 1105 entries (more granular dialogue separation)

### Binary Analysis (File 103)

**Speaker + Multi-part Dialogue Example:**
| Offset | Type | Index | Size | Data |
|--------|------|-------|------|------|
| 0x94768 | 0x02 | 1 | 8 | "Zara" (Speaker) |
| 0x94780 | 0x04 | 1 | 16 | "Let go of the" (Dialogue part 1) |
| 0x947A0 | 0x04 | 1 | 16 | "young lady...!" (Dialogue part 2) |

**Finding**: Type 0x02 speakers can be followed by multiple dialogue entries that form a complete sentence. The decompiler now correctly combines these parts while stopping at terminal punctuation to avoid over-combining.

### Known Issues
- Some dialogues without Type 0x02/0x03 speakers may still be incorrectly combined by the general dialogue combining logic
- Entries without speakers (orphan dialogues) require further investigation

## [1.1.4] - 2025-12-28

### Fixed
- **Entry index display regression**: Fixed issue where all entries showed "Entry 1" instead of sequential indices
  - Root cause: Code was using binary `Index` field directly (mostly 1) instead of sequential display indices
  - Solution: Added sequential display index counter in `write_output()`

- **Type 0x03 speakers not recognized**: Fixed speaker detection for Japanese speaker names stored as Type 0x03
  - Root cause: Code only checked Type 0x02 for speakers, but "パール" (Pearl) is stored as Type 0x03 in file 103
  - Solution: Extended speaker detection to handle both Type 0x02 and Type 0x03 entries

- **Text truncation regression**: Fixed issue where dialogue text was truncated or split incorrectly
  - Root cause: Overly strict index matching in Type 0x02 speaker handling prevented combining dialogue parts
  - Solution: Removed strict index matching and restored look-ahead combining for Type 0x02/0x03 speakers

### Changed
- `write_output()`: Added sequential display index counter for non-choice format files
- `combine_dialogue_entries()`: Type 0x02/0x03 speakers now look ahead and combine all consecutive Type 0x04/0x05/0x07 dialogue entries
- `combine_dialogue_entries()`: Extended to handle Type 0x03 entries in addition to Type 0x02 for speaker detection
- File 103: 2088 entries → 1394 entries (dialogue parts now combined correctly with speakers)

### Binary Analysis (File 103)

**Type 0x03 Speaker Entry Example:**
| Offset | Type | Index | Size | Data |
|--------|------|-------|------|------|
| 0x1E91C | 0x03 | 1 | 12 | "パール" (Pearl - speaker name in Katakana) |
| 0x1E940 | 0x05 | 1 | 16 | "雨やだよぉ。" (Dialogue text) |

**Finding**: Type 0x03 entries can also contain speaker names (not just Type 0x02). The decompiler now recognizes speaker names in both Type 0x02 and Type 0x03 entries.

## [1.1.3] - 2025-12-28

### Fixed
- **Type 0x05/0x07 speaker detection**: Fixed speaker assignment for dialogue split across Type 0x05 and 0x07 entries
  - Entry 22499 (File 103): "Come on, #Name[1],lets go outside right now!" now correctly shows Speaker: Pearl
  - Root cause: Type 0x02 speaker entries were only paired with the immediate next dialogue entry
  - Solution: Type 0x02 speakers now look ahead and combine ALL consecutive Type 0x05/0x07 entries with the same index

### Binary Analysis

**Entry 22499 (File 103) - Multi-segment dialogue:**
| Offset | Type | Index | Size | Data |
|--------|------|-------|------|------|
| 0x8A078 | 0x02 | 1 | 8 | "Pearl" (Speaker name) |
| 0x8A090 | 0x05 | 1 | 20 | "Come on, #Name[1]," (Dialogue part 1) |
| 0x8A0B8 | 0x07 | 1 | 28 | "lets go outside right now!" (Dialogue part 2) |

**Finding**: Type 0x05 and 0x07 are dialogue continuation types that share the same speaker
- All three entries have Index 1, indicating they belong to the same dialogue group
- The Type 0x02 speaker applies to both Type 0x05 and Type 0x07 dialogue parts
- Before fix: Created two separate entries, one with Speaker: Pearl, another with Speaker: #Name[1]
- After fix: Creates single combined entry with Speaker: Pearl and combined text

### Fixed
- **Speaker names filtered by bytecode pattern**: Fixed issue where speaker names were incorrectly filtered as bytecode
  - Root cause: Bytecode pattern `r'^[a-z]{3,5}$'` matched "Pearl", "Richie", etc. with re.IGNORECASE
  - Solution: Added early return in `_is_valid_text()` for recognized speaker names

### Changed
- `is_speaker_name()`: Now strips null bytes (`\x00`) in addition to whitespace
- `combine_dialogue_entries()`: Type 0x02 speakers now combine all consecutive Type 0x05/0x07 entries with same index
- `_is_valid_text()`: Added speaker name check before bytecode pattern matching
- File 103: 2134 entries → 2088 entries (46 multi-segment dialogues now combined)

## [1.1.2] - 2025-12-28

### Fixed
- **Character ID bytecode filtering**: Added patterns to filter additional bytecode variables
  - Entry 4327: `mejo07` (lowercase+digits)
  - Entry 4403: `cckraths01ht_kana` (incorrectly combined from `cck` + `raths01ht_kana`)

### Binary Analysis

**Entry 4327 (File 104):**
| Offset | Type | Index | Size | Data |
|--------|------|-------|------|------|
| 0x1C748 | 0x02 | 1 | 8 | "mejo07" (Type 0x02 speaker format) |
| 0x1C760 | 0x04 | 1 | 16 | "mejo07_kamae" (Type 0x04 dialogue format) |

**Entry 4403 (File 104) - Binary Investigation:**
| Offset | Type | Index | Size | Data |
|--------|------|-------|------|------|
| 0x1C540 | 0x01 | 1 | 4 | "cck" (short bytecode) |
| 0x1C550 | 0x03 | 1 | 12 | "cck_leon" (bytecode variable) |
| 0x1CFD8 | 0x02 | 1 | 8 | "raths01" (bytecode) |
| 0x1D000 | 0x04 | 1 | 16 | "raths01ht_kana" (complex variable) |

**Finding**: Combining logic incorrectly combined `cck` + `raths01ht_kana` → `cckraths01ht_kana`
- All entries are bytecode variables, not actual dialogue
- Need additional filter patterns for extended formats

### Changed
- Bytecode filter patterns (in `_is_valid_text()`):
  - Added: `r'^[a-z]+\d+[a-z]*_[a-z]+$'` - Extended variables (raths01ht_kana, allows letters after digits)
  - Added: `r'^[a-z]{3,5}$'` - Short bytecode identifiers (cck, suma, etc.)
  - Existing: `r'^[a-z]+\d+$'` - Simple lowercase+digits identifiers (mejo07, rath02)

## [1.1.1] - 2025-12-28

### Fixed
- **Broken decompiler output**: Fixed issue where output showed only 14-19 entries with incorrect "Entry 1" indices
  - Root cause: Experimental compact format parser was finding 417 entries (mostly bytecode) instead of dialogue
  - Solution: Reverted to legacy UTF-8 parser which correctly produces 40 entries
- **Binary structure documentation**: Documented actual binary format structure in STCM2L_FORMAT.md
  - Entry format: Type (4 bytes) + Index (4 bytes) + Size (4 bytes) + UTF-8 data
  - Valid types: 0x02, 0x03, 0x04, 0x0B, 0x0C
  - Binary Index field groups related entries but is not used for display
  - Display uses sequential indices (4218, 4233, etc.) based on UTF-8 string position

### Changed
- File 101.txt: Now correctly outputs 40 entries (was broken at 14-19 entries)
- All text is complete and properly formatted
- Updated `decompile_full_format()` to use `_parse_legacy_utf8()` instead of `_parse_compact_format()`
- Enhanced `_parse_compact_format()` to accept Types 0x0B and 0x0C (for future use)

### Technical Details
- Binary study revealed structured entry format at offsets like 0x1BDA0, 0x1E940, 0x1BF20
- Compact format parser finds too many bytecode entries (417) vs. dialogue entries (74)
- UTF-8 scanner approach produces correct output by filtering on text content validity
- Language mixing prevention was previously implemented using character detection (not ideal but functional)

### Investigated
- **#Name[X] binary structure**: Analyzed file 103 entries 4564 and 4567 to understand `#Name[X]` patterns
  - Finding: `#Name[X]` is **NOT** a separate binary field or speaker marker
  - `#Name[X]` is literally part of the UTF-8 text data stored in entries
  - Type 0x03 entries: Pure placeholder entries containing just `#Name[X]` (Size 12)
  - Type 0x0D entries: Dialogue text with `#Name[X]` embedded (e.g., `#Name[1]ちゃんは今日を...`)
  - Game engine replaces these placeholders with actual character names at runtime
  - Updated STCM2L_FORMAT.md with correct binary structure documentation

## [1.1.0] - 2025-12-28

### Added
- **Choice detection and grouping**: UI choice options now automatically detected and grouped
  - Short Japanese choice options (2-10 chars) are identified based on text patterns
  - Related choices grouped by proximity (within 50 index positions) with " / " separator
  - Marked with `[CHOICE]` tag in output header for easy identification
  - Example: `はい / いいえ` grouped as single entry with `[2 options: はい / いいえ]`
- **Choice metadata display**: Choice entries show option count and individual options
  - Format: `[N options: opt1 / opt2 / ...]` displayed below entry header
  - Helps translators see all choice options at a glance

### Changed
- File 101.txt: 39 entries → 38 entries (choices `はい` and `いいえ` now grouped)
- Choice detection based on text patterns (short Japanese, no terminal punctuation)
- Groups formed from consecutive choice candidates within 50 index positions

### Technical Details
- New method `is_choice_candidate()`: Detects UI choice options by text patterns
  - Short Japanese text (2-10 chars)
  - Not questions, not dialogue, not bytecode
  - Excludes same-vowel repetitions (あああ) but allows valid words (いいえ)
- New method `group_related_choices()`: Groups choices by proximity
  - Finds 2-5 choice candidates within 50 index positions
  - Creates combined entry with `is_choice=True` metadata
- Output formatting: `[CHOICE]` tag and options count in `write_output()`

## [1.0.4] - 2025-12-28

### Fixed
- **2-character Japanese word filtering**: Modified length checks to allow 2-character Japanese words (はい, いいえ, うん, etc.)
  - Type 0x04 handler (line 256-262): Added Japanese character detection to skip 3-char minimum for Japanese text
  - Type 0x02 handler (line 213-232): Added logic to keep short Japanese choice options even when not in speaker name list
  - Unknown type handler (line 299-309): Previously modified (same logic applied)
- **UI choice dialog preservation**: Prologue skip dialog now correctly shows all three options:
  - `プロローグをスキップしますか？` (Question)
  - `はい` (Yes option) - previously missing
  - `いいえ` (No option)

### Changed
- File 101.txt: 38 entries → 39 entries (added Entry 4695: `はい`)
- Overall output is more complete for Japanese UI elements and choice options

## [1.0.3] - 2025-12-28

### Fixed
- **Effect code and UI element filtering**: Added patterns to filter out effect codes (`ef_shake5`, `ef_flash`, etc.) and UI elements (`select`, `export_data`)
  - Fixed corrupted entries like `いいえselectselectef_shake5Rain, fine...` → now correctly outputs `いいえ`
  - Root cause: Full STCM2L format parser creates entries with bracketed notes `[select, ef_shake5, ...]` which were then incorrectly combined
- **Bracketed notes combining prevention**: Entries ending with `]` (bracketed notes format) are no longer combined with subsequent entries
- **Closing bracket as terminal punctuation**: Added `]` to terminal punctuation regex to prevent combining entries that end with bracketed notes

### Changed
- File 101.txt: Entry 4699 now correctly shows `いいえ` instead of corrupted `いいえselectselectef_shake5Rain, fine...`

## [1.0.2] - 2025-12-28

### Fixed
- **Entry combining for Japanese parentheses**: Split dialogue entries with Japanese `（` and `）` are now correctly combined
  - Example: `（それに比べて、` + `この塔はなんて平和なんだろう）` → `（それに比べて、この塔はなんて平和なんだろう）`
  - Added Japanese closing parenthesis `）` to terminal punctuation detection
  - Added Japanese parenthesis counting to unmatched parenthesis check
  - Added Japanese opening parenthesis `（` to continuation marker detection
- **Implemented actual combining logic**: The `should_combine_entries()` function is now called in a look-ahead loop
- **Speaker name detection**: Legacy UTF-8 parser now detects speaker names (Pearl, Richie, etc.) and marks them as Type 0x02
- **Bytecode filtering improvements**: Enhanced patterns to filter out bytecode identifiers like `Rath_bad_end`, `FavPearl`, etc.
- **Binary garbage filtering**: Added checks for control characters and short invalid strings

### Changed
- File 116.txt: 232 entries → 128 entries (30% reduction via combining)
- Overall output is more compact and readable for translators

### Binary Structure Discovery
- Dialogue entries are stored as **separate physical entries** in the binary file
- Example: `（それに比べて、` at 0x1C91C and `この塔はなんて平和なんだろう）` at 0x1CFB7 (1691 bytes apart)
- Game engine uses separate entries for display timing and text effects
- Decompiler now correctly combines them based on linguistic patterns

## [1.0.1] - 2025-12-28

### Fixed
- Filter out bytecode instructions (switch, bgXXXX, @commands, character IDs)
- Combine split dialogue lines into single coherent entries
- Preserve #Name[X] indicators in output (character name indicators for translators)

### Changed
- Dialogue continuation detection for parenthetical and split sentences
- Entries now show combined_from range when applicable
- #Name[X] indicators are placed on their own line before dialogue text (as speaker label)

### Format Discoveries
- Full STCM2L format stores dialogue as separate null-terminated strings
- #Name[X] patterns are character name indicators, kept for translator context
- Character reference codes (edga01, etc.) are bytecode and are filtered out

## [1.0.0] - 2025-12-28

### Added
- Initial STCM2L decompiler implementation
- Support for dialogue format files (type 1, 2, 11 entries)
- Speaker name extraction for multiple character types:
  - `yougo*` - Player character dialogue
  - `her01*`, `zara0*`, `ness0*`, `pear0*`, `rich0*`, `rath0*`, `elza0*`, `tiara*`
- UTF-8 Japanese text decoding
- Multi-segment text extraction per entry (longest = main dialogue)
- Line break handling (#n → newline conversion)
- Bytecode instruction filtering:
  - Skips `memory_init`, `memory_exit`, `COLLECTION_LINK`
  - Skips `scene_play`, `suma` variable
  - Skips `@X!` control patterns
- Full STCM2L format string extraction
- Batch processing for entire SCRIPT directories
- Pattern-based entry header detection
- `--version` / `-v` CLI flag

### File Format Documentation
- **Dialogue Format**: 8-byte header + variable-length entries
- **Entry Structure**: type(2) + index(2) + speaker + text_segments
- **Text Segments**: Separated by 0x00/0xFF padding, longest segment = main dialogue
- **Full STCM2L Format**: GLOBAL_DATA + CODE_START_ bytecode sections

See `STCM2L_FORMAT.md` for detailed format documentation.

### Known Limitations
- Full STCM2L format extracts strings but doesn't parse bytecode
- Some entries may have missing text if format variations exist
- Speaker prefixes are hardcoded (could be data-driven in future)

### Tested Files
- 114/119 SCRIPT files successfully decompiled
- File 10: 136 dialogue entries with full Japanese text
- Known working: 10, 101, 102, 103, 104, 105, 106, 107, 108, 109, 111, 112...

### Known Issues
- 5 files did not decompile (see `PROBLEMATIC_FILES.md` for details)
- Some speaker prefixes may be missing from hardcoded list

### Documentation
- `STCM2L_FORMAT.md` - Complete file format reference
- `CHANGELOG.md` - This version history file
- `README.md` - User guide and usage examples
- `VERSION_POLICY.md` - Version update guidelines

---

## Version Policy

For version update guidelines, see `VERSION_POLICY.md`.
