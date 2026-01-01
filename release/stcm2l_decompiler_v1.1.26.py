#!/usr/bin/env python3
"""
STCM2L Script Decompiler v1.1.25

Decompiles STCM2L binary script files to readable text format for translation.

Supports two formats:
- Dialogue format: Files with speaker names and Japanese dialogue text
- Full STCM2L format: Files with GLOBAL_DATA and CODE_START_ bytecode sections

See CHANGELOG.md for full version history.
"""

__version__ = "1.1.26"
__author__ = "STCM2L Decompilation Project"
# Output directory derived from version (e.g., v1.1.12 -> decompiled_v1.1.12/)
OUTPUT_DIR = f"decompiled_v{__version__}"

import os
import sys
import struct
import re
from pathlib import Path
from typing import List, Tuple, Optional


class STCM2LDecompiler:
    """Decompiler for STCM2L script files."""

    # Entry types based on analysis
    ENTRY_TYPE_DIALOGUE = 1
    ENTRY_TYPE_CHOICE = 2
    ENTRY_TYPE_SCENE = 3
    ENTRY_TYPE_COMMAND = 4
    ENTRY_TYPE_UNKNOWN = 5

    # Bytecode patterns to filter out (NOT including #Name[X] - those are kept as speaker labels)
    BYTECODE_PATTERNS = [
        r'switch', 'case', 'default',  # Control flow
        r'bg[0-9a-f]+',        # Background references
        r'@[a-zA-Z0-9_]+',     # @ prefixed commands
        r'^(edga|her|zara|ness|pear|rich|rath|elza|haniy|zk)[0-9]+[a-z]*',  # Character IDs (with numbers)
        r'suma$',              # Variable name
        r'scene_play$',        # Instruction
        r'flg_memory$',        # Variable name
        r'^@[a-zA-Z0-9_]+$',   # @ prefixed single words
    ]

    # Full character names that act as speaker labels (from Type 0x02 entries)
    # These should NOT be filtered - they indicate speaker changes
    SPEAKER_NAMES = {
        # English names (case-insensitive)
        'pearl', 'richie', 'nesso', 'zara', 'edgar', 'elza', 'rath',
        'guillan', 'arles', 'henrietta',
        # Katakana names (Japanese)
        'パール', 'リッチー', 'ネッソ', 'ザラ', 'エドガー', 'エルザ', 'ラス',
        'ギラン', 'アルル', 'ヘンリエッタ'
    }

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.data = None
        self.entries = []

    def read_file(self) -> bool:
        """Read the binary file."""
        try:
            with open(self.filepath, 'rb') as f:
                self.data = f.read()
            return True
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            return False

    def detect_format(self) -> str:
        """Detect which STCM2L format the file uses."""
        if not self.data:
            return "unknown"

        # Check for full STCM2L header format
        if self.data[:6] == b'STCM2L':
            return "full"

        # Check for dialogue format (starts with entry count)
        if len(self.data) >= 8:
            # First 4 bytes might be entry count
            entry_count = struct.unpack('<I', self.data[:4])[0]
            if entry_count < 10000:  # Reasonable entry count
                return "dialogue"

        return "unknown"

    def is_bytecode(self, text: str) -> bool:
        """Check if text matches a bytecode pattern that should be filtered out."""
        text = text.strip()

        # v1.1.13: Known English UI choice words are NOT bytecode (from Type 0x01 entries)
        ENGLISH_CHOICE_WORDS = {'yes', 'no', 'ok', 'cancel', 'accept', 'decline', 'close'}
        if text.lower() in ENGLISH_CHOICE_WORDS:
            return False

        # Check against known bytecode patterns
        for pattern in self.BYTECODE_PATTERNS:
            if re.match(pattern, text, re.IGNORECASE):
                return True

        # Check for bytecode-heavy content (many @ symbols, short character sequences)
        # Split text into words and check if majority look like bytecode
        words = text.split()
        if len(words) > 5:
            bytecode_count = 0
            for word in words:
                # Count words that look like bytecode
                if (word.startswith('@') or
                    re.match(r'^[a-z]{1,3}$', word) or  # very short words
                    re.match(r'^[a-z]+\d+$', word) or   # alphanumeric codes
                    len(word) < 3):
                    bytecode_count += 1
            # v1.1.10: Increased threshold from 60% to 85% to avoid false positives on English dialogue
            # Normal English with short words ("to", "for", "had") was being misidentified as bytecode
            if bytecode_count / len(words) > 0.85:
                return True

        return False

    def is_name_indicator(self, text: str) -> bool:
        """Check if text is a #Name[X] character indicator (KEEP these in output)."""
        return bool(re.match(r'^#Name\[[0-9]+\]$', text.strip()))

    def is_speaker_name(self, text: str) -> bool:
        """Check if text is a character name (speaker label from Type 0x02 entries)."""
        # Strip whitespace AND null bytes (binary padding)
        text = text.strip().strip('\x00')
        text = text.lower()
        return text in self.SPEAKER_NAMES

    def should_combine_entries(self, prev_entry: dict, curr_entry: dict) -> bool:
        """Check if current entry continues previous dialogue."""
        prev_text = prev_entry.get('text', '')
        curr_text = curr_entry.get('text', '')

        # Don't combine if current is bytecode or name indicator
        if self.is_bytecode(curr_text) or self.is_name_indicator(curr_text):
            return False

        # Don't combine entries with bracketed notes format (v1.0.3)
        # This indicates multi-segment data from full STCM2L format parser
        # e.g., "いいえ [select, ef_shake5, ...]" - these should not combine further
        if ' [' in prev_text and prev_text.rstrip().endswith(']'):
            return False

        # Check for language mixing - don't combine Japanese with English or vice versa
        prev_has_japanese = any('\u3000' <= c <= '\u9fff' for c in prev_text)
        prev_has_english = sum(1 for c in prev_text if c.isalpha()) > 2
        curr_has_japanese = any('\u3000' <= c <= '\u9fff' for c in curr_text)
        curr_has_english = sum(1 for c in curr_text if c.isalpha()) > 2

        # v1.1.16: Don't combine if current text has both Japanese AND significant English (romaji)
        # This catches cases like "痛い……！" where romaji makes it look like English
        # Such text should NOT combine with either pure Japanese or pure English entries
        if curr_has_japanese and curr_has_english:
            return False

        # Don't combine if language switches (Japanese → English or English → Japanese)
        if (prev_has_japanese and curr_has_english and not curr_has_japanese):
            return False
        if (prev_has_english and curr_has_japanese and not curr_has_english):
            return False

        # Check for various continuation patterns
        # 1. Previous ends without terminal punctuation (and is reasonably long)
        # v1.0.3: Added \] to treat closing bracket as terminal punctuation
        # v1.1.15: Added … (horizontal ellipsis U+2026) to terminal punctuation
        if len(prev_text) > 3 and not re.search(r'[。！？\.!?\"』）\]…]', prev_text):
            # Allow combination if current entry continues the thought
            # (even if it starts with capital - might be proper noun or continuation)
            return True

        # 2. Current starts with lowercase or continuation marker
        if re.match(r'^[a-z(「『（]', curr_text):
            return True

        # 3. Parenthetical continuation - prev has open paren without close
        # Check for both ASCII and Japanese parentheses
        open_parens = prev_text.count('(') + prev_text.count('（')
        close_parens = prev_text.count(')') + prev_text.count('）')
        if open_parens > close_parens:
            return True

        return False

    def is_choice_candidate(self, entry: dict) -> bool:
        """
        Determine if an entry is a UI choice option.

        Choice indicators from binary analysis:
        - Short Japanese text (2-10 characters)
        - Not in speaker name list
        - Not matching bytecode patterns
        - Not a question (doesn't end with ？)
        - v1.1.13: Type 0x02 entries with short English text (from Type 0x01) are also choices

        Note: Type check is limited since _parse_legacy_utf8 assigns most entries as Type 0x04.
        Detection is based on text patterns instead.

        Returns True if entry is a choice candidate.
        """
        text = entry.get('text', '').strip()
        entry_type = entry.get('type', 0)

        # Length check: choices are short (2-10 chars)
        text_len = len(text)
        if text_len < 2 or text_len > 10:
            return False

        # v1.1.13: Type 0x02 entries with short English text are choice options (from Type 0x01)
        # But only recognize known English UI choice words, not any short English text
        if entry_type == 0x02:
            has_japanese = any('\u3000' <= c <= '\u9fff' for c in text)
            if not has_japanese:
                # Only known English choice words are choice candidates
                ENGLISH_CHOICE_WORDS = {'yes', 'no', 'ok', 'cancel', 'accept', 'decline', 'close'}
                if text.lower() in ENGLISH_CHOICE_WORDS:
                    return True
                else:
                    # Other Type 0x02 without Japanese are NOT choice candidates (e.g., "ed")
                    return False

        # Must contain Japanese characters (for regular Japanese choices)
        has_japanese = any('\u3000' <= c <= '\u9fff' for c in text)
        if not has_japanese:
            return False

        # Must not be a speaker name
        if self.is_speaker_name(text):
            return False

        # Must not be bytecode
        if self.is_bytecode(text):
            return False

        # Exclude questions (end with ？ or か？)
        if text.endswith('？') or text.endswith('か？'):
            return False

        # Exclude same-vowel repetitions (meaningless sounds like あああ, いいい)
        # But not valid words like いいえ (no) or ええ (yes)
        if len(text) >= 2 and len(set(text)) == 1 and re.match(r'^[あいうえお]+$', text):
            return False
        if re.match(r'^[。！？]+$', text):
            return False

        # Exclude entries with terminal punctuation (dialogue)
        if re.search(r'[。！』）」]$', text):
            return False

        return True

    def group_related_choices(self, entries: List[dict]) -> List[dict]:
        """
        Group choice options that are near each other in the entry sequence.

        Strategy:
        1. Find all choice candidates using is_choice_candidate()
        2. Group candidates that are within 50 index positions of each other
        3. Create combined entries with ' / ' separator
        4. Mark with is_choice=True metadata

        Returns modified entries list with grouped choices.
        """
        # Find all choice candidates
        choice_candidates = []
        for entry in entries:
            if self.is_choice_candidate(entry):
                choice_candidates.append(entry)

        if not choice_candidates:
            return entries

        # Group related choices (within 50 index positions)
        grouped = []
        i = 0
        while i < len(choice_candidates):
            current = choice_candidates[i]
            current_index = current.get('index', 0)
            current_text = current.get('text', '').strip()

            # Start a new group
            group = [current]
            j = i + 1

            # Find nearby choices (within 50 index positions)
            while j < len(choice_candidates):
                next_choice = choice_candidates[j]
                next_index = next_choice.get('index', 0)

                if next_index - current_index <= 50:
                    group.append(next_choice)
                    j += 1
                else:
                    break

            # Only create combined entry if group has 2-5 options
            if 2 <= len(group) <= 5:
                choice_texts = [e.get('text', '').strip() for e in group]
                combined_text = ' / '.join(choice_texts)

                # Mark entries for removal
                for e in group:
                    e['_remove'] = True

                # Create combined choice entry
                combined_entry = {
                    'index': group[0].get('index'),
                    'text': combined_text,
                    'speaker': '',
                    'type': 0x02,  # Use Type 2 for choices
                    'is_choice': True,
                    'choice_count': len(choice_texts),
                    'choice_options': choice_texts
                }

                grouped.append(combined_entry)

            i = j if j > i + 1 else i + 1

        # Remove marked entries and add grouped ones
        result = [e for e in entries if not e.get('_remove', False)]
        result.extend(grouped)

        # Sort by index
        result.sort(key=lambda e: e.get('index', 0))

        return result

    def combine_dialogue_entries(self, entries: List[dict]) -> List[dict]:
        """Combine split dialogue entries and filter out bytecode, with speaker separation."""
        combined = []
        i = 0
        while i < len(entries):
            current = entries[i]
            current_text = current.get('text', '')
            current_type = current.get('type', 0)

            # Handle Type 0x02 and 0x03 entries (speaker names / bytecode indicators)
            # v1.1.6: Both Type 0x02 and 0x03 can contain speaker names
            # Binary format: Type 0x02 speaker → ONE OR MORE dialogue entries → Type 0x02 speaker
            # Combine consecutive dialogues after speaker until next speaker or terminal punctuation
            if current_type in (0x02, 0x03):
                # Check if this is a speaker name
                if self.is_speaker_name(current_text):
                    # This is a speaker name - look ahead for consecutive dialogue entries
                    speaker = current_text
                    i += 1

                    dialogue_parts = []
                    while i < len(entries):
                        next_entry = entries[i]
                        next_type = next_entry.get('type', 0)
                        next_text = next_entry.get('text', '')

                        # v1.1.10: Combine Type 0x04, 0x05, 0x06, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E dialogue entries (exclude 0x07, 0x0F, 0x12 narration)
                        # v1.1.20: Removed 0x07 from combine list - Type 0x07 has separate logic to detect dialogue vs narration
                        # v1.1.22: Removed 0x0F from combine list - Type 0x0F can be dialogue OR narration
                        # v1.1.13: Added 0x01 to exclude list - Type 0x01 choice options should NOT combine with dialogue
                        # v1.1.14: Added 0x03 to combine list - Type 0x03 can be dialogue continuation (e.g., "a Lobeira.")
                        # v1.1.15: Added 0x0D, 0x0E to combine list - Type 0x0D, 0x0E are dialogue continuation types
                        # v1.1.18: Added 0x10 to combine list - Type 0x10 is dialogue continuation type
                        # v1.1.19: Added 0x11 to combine list - Type 0x11 is dialogue continuation type
                        # v1.1.25: Added 0x0C to combine list - Type 0x0C dialogue with speaker should combine
                        if next_type not in (0x01, 0x03, 0x04, 0x05, 0x06, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11):
                            break

                        # Stop at #Name[X] indicators (speaker change)
                        if self.is_name_indicator(next_text):
                            break

                        # v1.1.26: Stop combining if entry starts with "--" (structural marker for speaker change)
                        # Binary analysis shows this pattern indicates entry should NOT combine with previous speaker
                        if next_text.strip().startswith('"--'):
                            break

                        # Stop if text ends with terminal punctuation (. ! ? 。 ！ ？)
                        # v1.1.23: Added ASCII period (.) to prevent combining complete sentences with new sentences
                        # v1.1.24: Continue combining Type 12/13 entries after terminal punctuation
                        # v1.1.25: Enhanced quote matching to look multiple entries ahead for quote closure
                        # v1.1.25: Don't treat ... (ellipsis) as terminal punctuation
                        stripped_text = next_text.rstrip()
                        # Check if ends with terminal punctuation, but NOT ellipsis (...)
                        ends_with_punct = (
                            stripped_text.endswith(('.', '!', '?', '\u3002', '\uff01', '\uff0f')) and
                            not stripped_text.endswith('...') and
                            not stripped_text.endswith('。。。')
                        )
                        if ends_with_punct:
                            dialogue_parts.append(next_text)
                            i += 1

                            # Check if we need to continue for quote closure (multi-entry lookahead)
                            combined_check = ' '.join(dialogue_parts)
                            if combined_check.count('"') % 2 == 1:  # Odd quotes = unclosed
                                # Look ahead for quote closure across multiple entries
                                while i < len(entries):
                                    next_type = entries[i].get('type', 0)
                                    next_text_check = entries[i].get('text', '')

                                    # Type 12/13: Always continue (narration between dialogue parts)
                                    if next_type in (0x0C, 0x0D):
                                        dialogue_parts.append(next_text_check)
                                        i += 1
                                        continue

                                    # Type 4/6/3/15: Check if it closes the quote
                                    if next_type in (0x04, 0x06, 0x03, 0x0F):
                                        # If entry has any quotes, add it and check if quote is now closed
                                        if next_text_check.count('"') > 0:
                                            dialogue_parts.append(next_text_check)
                                            i += 1
                                            # Check if quote is now closed
                                            combined_check = ' '.join(dialogue_parts)
                                            if combined_check.count('"') % 2 == 0:
                                                break  # Quote closed, stop combining
                                            # Quote still unclosed, continue to next entry
                                            continue
                                        # No quote found but might be continuation text
                                        # Only continue if it's part of trailing speech (lowercase start, no terminal punctuation)
                                        elif next_text_check and not next_text_check[0].isupper():
                                            dialogue_parts.append(next_text_check)
                                            i += 1
                                            continue
                                        else:
                                            # Capital letter start = likely new sentence, stop combining
                                            break
                                    else:
                                        # Different type, stop combining
                                        break

                            break  # Break if no unclosed quote or quote was closed

                        # Skip bytecode entries
                        if self.is_bytecode(next_text):
                            i += 1
                            continue

                        # v1.1.16: Check for language mixing - don't combine Japanese with English
                        # This catches cases like "痛い……！" where romaji makes it look like English
                        next_has_japanese = any('\u3000' <= c <= '\u9fff' for c in next_text)
                        next_has_english = sum(1 for c in next_text if c.isalpha()) > 2
                        if next_has_japanese and next_has_english:
                            # Current text has both Japanese AND English (romaji) - stop combining
                            break

                        # v1.1.16: Check if combining with previous dialogue_parts would mix languages
                        if dialogue_parts:
                            combined_so_far = ' '.join(dialogue_parts)
                            combined_has_japanese = any('\u3000' <= c <= '\u9fff' for c in combined_so_far)
                            combined_has_english = sum(1 for c in combined_so_far if c.isalpha()) > 2
                            # Don't combine if language would switch
                            if (combined_has_japanese and next_has_english and not next_has_japanese):
                                break
                            if (combined_has_english and next_has_japanese and not next_has_english):
                                break

                        # v1.1.22: Don't combine if previous entry ended with sentence punctuation
                        # and current entry starts with a capital letter (likely new sentence/narration)
                        # Exception: "I'm", "I ", etc. are first-person continuations, not new sentences
                        # v1.1.25: Also skip capital letter check if there's an unclosed quote
                        # v1.1.25: Don't treat ... (ellipsis) as terminal punctuation
                        if dialogue_parts and next_text:
                            prev_ended = dialogue_parts[-1].rstrip()
                            # Check for sentence-ending punctuation (including ASCII period), but NOT ellipsis
                            prev_ends_punct = (
                                prev_ended.endswith(('.', '!', '?', '\u3002', '\uff01', '\uff0f')) and
                                not prev_ended.endswith('...') and
                                not prev_ended.endswith('。。。')
                            )
                            if prev_ends_punct:
                                # v1.1.25: Check if combined text has unclosed quote before capital letter check
                                combined_check = ' '.join(dialogue_parts)
                                if combined_check.count('"') % 2 == 1:  # Odd quotes = unclosed
                                    # Unclosed quote, continue combining regardless of capital letter
                                    pass  # Don't break, let the combining continue
                                elif next_text[0].isupper():
                                    # First-person "I" is a continuation, not a new sentence
                                    if not next_text.startswith("I'm") and not next_text.startswith("I "):
                                        break

                        dialogue_parts.append(next_text)
                        i += 1

                    # If we found dialogue parts, create a combined entry
                    if dialogue_parts:
                        # Join with space between parts
                        combined_text = dialogue_parts[0]
                        for part in dialogue_parts[1:]:
                            if combined_text and not combined_text[-1] in (' ', '\n'):
                                combined_text += ' '
                            combined_text += part

                        combined.append({
                            'index': current.get('index'),
                            'text': combined_text,
                            'speaker': speaker,
                            'type': 0x04
                        })

                    continue
                else:
                    # v1.0.4: Type 0x02/0x03 but not a speaker name - could be bytecode OR short Japanese choice options
                    # Check if it's a short Japanese word (はい, いいえ, etc.)
                    text_len = len(current_text.strip())
                    has_japanese = any('\u3000' <= c <= '\u9fff' for c in current_text)
                    if text_len >= 2 and has_japanese and not self.is_bytecode(current_text):
                        # This is a Japanese choice option or UI text - keep it
                        combined.append({
                            'index': current.get('index'),
                            'text': current_text,
                            'speaker': '',
                            'type': current_type
                        })
                        i += 1
                        continue
                    else:
                        # v1.1.14: Check if it's bytecode before skipping
                        # Type 0x03 can contain English dialogue continuation (e.g., "a Lobeira.")
                        # v1.1.14: Type 0x03 name indicators (#Name[X]) should be skipped
                        if self.is_name_indicator(current_text):
                            # Name indicator - skip it (will be found by look-back logic)
                            i += 1
                            continue
                        elif not self.is_bytecode(current_text):
                            # Not bytecode - keep it as dialogue text
                            combined.append({
                                'index': current.get('index'),
                                'text': current_text,
                                'speaker': '',
                                'type': current_type
                            })
                            i += 1
                            continue
                        else:
                            # Bytecode - skip it
                            i += 1
                            continue

            # v1.1.7: Handle Type 0x12 entries - these are narration and should NOT have speakers
            if current_type == 0x12:
                # Skip bytecode entries
                if self.is_bytecode(current_text):
                    i += 1
                    continue

                # Type 0x12 entries are narration - NO speakers, NO combining with dialogue
                combined.append({
                    'index': current.get('index'),
                    'text': current_text,
                    'speaker': '',  # Narration has no speaker
                    'type': 0x12
                })
                i += 1
                continue

            # v1.1.13: Handle Type 0x01 entries - these are English UI choice options (Yes, No, OK, etc.)
            # Convert to Type 0x02 for consistency with existing choice format
            # These will be grouped by group_related_choices() later
            # Only known English choice words are converted - other Type 0x01 entries are filtered as garbage
            if current_type == 0x01:
                # v1.1.13: Only known English choice words should be converted to Type 0x02
                # All other Type 0x01 entries (like "ed") are treated as garbage and skipped
                ENGLISH_CHOICE_WORDS = {'yes', 'no', 'ok', 'cancel', 'accept', 'decline', 'close'}
                if current_text.lower() not in ENGLISH_CHOICE_WORDS:
                    i += 1
                    continue

                combined.append({
                    'index': current.get('index'),
                    'text': current_text,
                    'speaker': '',  # Choice options have no speaker
                    'type': 0x02  # Convert to Type 0x02 for consistency
                })
                i += 1
                continue

            # v1.1.7: Handle Type 0x07 entries - can be dialogue OR narration continuation
            if current_type == 0x07:
                # Skip bytecode entries
                if self.is_bytecode(current_text):
                    i += 1
                    continue

                # Check if this Type 0x07 entry is paired with a preceding speaker
                # Look backward for a Type 0x02/0x03 speaker entry
                has_speaker = False
                speaker_name = None
                j = i - 1
                while j >= 0:
                    prev_entry = entries[j]
                    prev_type = prev_entry.get('type', 0)
                    if prev_type in (0x02, 0x03):
                        prev_text = prev_entry.get('text', '')
                        if self.is_speaker_name(prev_text):
                            # Found a speaker - this is dialogue continuation
                            has_speaker = True
                            speaker_name = prev_text
                            break
                        else:
                            # Type 0x02/0x03 but not a speaker name - bytecode, stop looking
                            break
                    elif prev_type in (0x04, 0x05, 0x06, 0x07, 0x0D, 0x0E, 0x12):
                        # Another dialogue/narration entry - no speaker for this Type 0x07
                        break
                    else:
                        j -= 1

                # v1.1.11: Look ahead to combine Type 0x07 entries with same index
                # v1.1.15: Extended to combine Type 0x07 with ALL dialogue continuation types
                combined_text = current_text
                j = i + 1

                while j < len(entries):
                    next_entry = entries[j]
                    next_type = next_entry.get('type', 0)
                    next_text = next_entry.get('text', '')
                    next_index = next_entry.get('index', 0)

                    # v1.1.15: Only combine with dialogue continuation types (0x03-0x0E except 0x12)
                    # Type 0x07 + Type 0x07 still requires same index (original behavior)
                    # But Type 0x07 + Type 0x05/0x06/etc. can combine regardless of index
                    if next_type not in (0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E):
                        break

                    # For Type 0x07 + Type 0x07, require same index (preserve original behavior)
                    # But allow combining with other types regardless of index
                    if next_type == 0x07 and next_index != current.get('index', 0):
                        break

                    # Don't cross name indicator boundaries
                    if self.is_name_indicator(next_text):
                        break

                    # Skip bytecode entries
                    if self.is_bytecode(next_text):
                        j += 1
                        continue

                    # Combine the text
                    if combined_text and not combined_text[-1] in (' ', '\n'):
                        combined_text += ' '
                    combined_text += next_text
                    i += 1  # Skip this entry in the main loop
                    j += 1

                if has_speaker:
                    # This is dialogue continuation - combine with speaker
                    combined.append({
                        'index': current.get('index'),
                        'text': combined_text,
                        'speaker': speaker_name,
                        'type': 0x07
                    })
                else:
                    # This is narration continuation - no speaker
                    combined.append({
                        'index': current.get('index'),
                        'text': combined_text,
                        'speaker': '',
                        'type': 0x07
                    })
                # i was already incremented in the combining loop
                i += 1
                continue

            # Handle Type 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11 entries (dialogue only) - v1.1.10: exclude 0x12 narration
            # v1.1.15: Added 0x0D, 0x0E to type list
            # v1.1.18: Added 0x10 to type list
            # v1.1.19: Added 0x11 to type list
            # v1.1.25: Added 0x0F to type list (Type 0x0F consecutive entries should combine)
            if current_type in (0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11):
                # Check for #Name[X] indicators before this dialogue
                name_indicator = None
                j = i - 1
                while j >= 0:
                    prev_entry = entries[j]
                    prev_text = prev_entry.get('text', '')
                    prev_type = prev_entry.get('type', 0)
                    if self.is_name_indicator(prev_text):
                        name_indicator = prev_text
                        j -= 1
                    elif prev_type in (0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11):  # v1.1.25: Added 0x0F
                        # v1.1.14: Stop at any previous dialogue entry (not just Type 0x04)
                        # This prevents looking too far back across multiple dialogues
                        break
                    elif prev_type == 0x02 and not name_indicator:
                        # v1.1.14: If no name indicator found yet, continue past Type 0x02 speakers
                        # This allows finding name indicators that come before speaker entries
                        j -= 1
                    else:
                        j -= 1

                # Skip bytecode-only dialogue
                if self.is_bytecode(current_text):
                    i += 1
                    continue

                # v1.0.4: Skip entries that don't have meaningful content
                # For Japanese text, 2 characters can be a complete word (はい, いいえ, etc.)
                text_len = len(current_text.strip())
                has_japanese = any('\u3000' <= c <= '\u9fff' for c in current_text)
                if text_len < 3 and not (text_len >= 2 and has_japanese):
                    i += 1
                    continue

                # NEW: Look ahead to combine with next entries
                combined_text = current_text
                j = i + 1
                while j < len(entries):
                    next_entry = entries[j]
                    next_type = next_entry.get('type', 0)
                    next_text = next_entry.get('text', '')

                    # v1.1.10: Combine Type 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C dialogue entries (exclude 0x12)
                    # v1.1.13: Added 0x01 to exclude list - Type 0x01 choice options should NOT combine with dialogue
                    # v1.1.14: Added 0x03 to combine list - Type 0x03 can be dialogue continuation (e.g., "a Lobeira.")
                    # v1.1.15: Added 0x0D, 0x0E to combine list - Type 0x0D, 0x0E are dialogue continuation types
                    # v1.1.18: Added 0x10 to combine list - Type 0x10 is dialogue continuation type
                    # v1.1.19: Added 0x11 to combine list - Type 0x11 is dialogue continuation type
                    # v1.1.25: Added 0x0F to combine list - Type 0x0F consecutive entries should combine
                    # Type 0x0B/0x0C can be followed by Type 0x0A continuation
                    if next_type not in (0x01, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11):
                        break

                    # Don't cross name indicator boundaries
                    if self.is_name_indicator(next_text):
                        break

                    # v1.1.10: Don't skip bytecode check for Type 0x0A dialogue entries
                    # v1.1.14: Also don't skip Type 0x03 - can be dialogue continuation (e.g., "a Lobeira.")
                    # Type 0x0A and Type 0x03 entries are valid dialogue and may have short words
                    if next_type not in (0x03, 0x0A) and self.is_bytecode(next_text):
                        j += 1
                        continue

                    # Check for language mixing in the combined text + next text
                    # Don't combine if combining would mix Japanese and English
                    combined_has_japanese = any('\u3000' <= c <= '\u9fff' for c in combined_text)
                    combined_has_english = sum(1 for c in combined_text if c.isalpha() and ord(c) < 128) > 2
                    next_has_japanese = any('\u3000' <= c <= '\u9fff' for c in next_text)
                    next_has_english = sum(1 for c in next_text if c.isalpha() and ord(c) < 128) > 2

                    # Don't combine if language switches (Japanese → English or English → Japanese)
                    if (combined_has_japanese and next_has_english and not next_has_japanese):
                        break
                    if (combined_has_english and next_has_japanese and not next_has_english):
                        break

                    # Check if we should combine based on linguistic patterns
                    if self.should_combine_entries({'text': combined_text}, {'text': next_text}):
                        # v1.1.7: Add space between parts if needed (same logic as Type 0x02 speaker combining)
                        if combined_text and not combined_text[-1] in (' ', '\n'):
                            combined_text += ' '
                        combined_text += next_text
                        j += 1
                    else:
                        break

                # Update index to skip combined entries (will be incremented to j at loop end)
                i = j - 1

                # Prepend name indicator if present
                if name_indicator:
                    combined_text = f"{name_indicator}\n{combined_text}"

                # Final check for meaningful content
                has_japanese = any('\u3000' <= c <= '\u9fff' for c in combined_text)
                has_english = len([c for c in combined_text if c.isalpha()]) > 3
                if has_japanese or has_english:
                    combined.append({
                        'index': current.get('index'),
                        'text': combined_text,
                        'speaker': name_indicator if name_indicator else '',
                        'type': current_type
                    })
                i += 1
                continue

            # Unknown type - use bytecode check
            if self.is_bytecode(current_text):
                i += 1
                continue

            # v1.0.4: For Japanese text, 2 characters can be a complete word (はい, うん, etc.)
            text_len = len(current_text.strip())
            has_japanese = any('\u3000' <= c <= '\u9fff' for c in current_text)
            if text_len >= 3 or (text_len >= 2 and has_japanese):
                combined.append({
                    'index': current.get('index'),
                    'text': current_text,
                    'speaker': '',
                    'type': current_type
                })
            i += 1

        # Group related choice options
        combined = self.group_related_choices(combined)

        return combined

    def decode_utf8_string(self, data: bytes, start: int) -> Tuple[str, int]:
        """
        Decode a UTF-8 string from binary data.
        Returns (decoded_string, bytes_consumed).
        """
        end = start
        while end < len(data):
            if data[end] == 0x00:
                break
            end += 1

        raw_bytes = data[start:end]
        try:
            return raw_bytes.decode('utf-8', errors='replace'), end - start + 1
        except:
            # Fallback: try to decode as latin-1 and preserve characters
            return raw_bytes.decode('latin-1', errors='replace'), end - start + 1

    def decompile_dialogue_format(self) -> List[dict]:
        """
        Decompile the dialogue format (file 10 style).

        Format structure:
        - 8 bytes header: entry_count (4) + unknown (4)
        - Variable-length entries with pattern: type (2) + index (2) + speaker + text
        """
        entries = []

        if len(self.data) < 8:
            return entries

        # Read header
        entry_count = struct.unpack('<I', self.data[0:4])[0]
        entry_type_header = struct.unpack('<I', self.data[4:8])[0]

        # Detect format type
        is_choice_format = (entry_type_header == 8)
        format_name = "Choice/Branch Dialogue (Type 8)" if is_choice_format else "Dialogue"

        print(f"  Format: {format_name} (count={entry_count}, type={entry_type_header})", file=sys.stderr)

        # Store format type for later use
        self.is_choice_format = is_choice_format

        # Search for entry headers by pattern
        # Pattern: XX00 YY00 where XX and YY are small integers (entry type and index)
        # The entry is often followed by a speaker name

        pos = 8  # Start after file header
        entry_num = 0
        max_entries = entry_count

        # First, find all potential entry headers
        entry_offsets = []
        for i in range(len(self.data) - 12):
            # Look for pattern: byte1=0x00, byte3=0x00
            # This indicates potential type (2 bytes) + index (2 bytes) structure
            if i + 4 >= len(self.data):
                break
            if self.data[i + 1] == 0x00 and self.data[i + 3] == 0x00:
                # Check if this looks like a valid entry header
                entry_type = struct.unpack('<H', self.data[i:i+2])[0]
                entry_index = struct.unpack('<H', self.data[i+2:i+4])[0]
                # Valid types seem to be small positive integers
                if 1 <= entry_type <= 100 and 1 <= entry_index <= max_entries:
                    # Check if followed by 'yougo' speaker name pattern
                    if i + 9 < len(self.data):
                        # Check for common speaker prefixes
                        speaker_prefix = self.data[i+4:i+9]
                        # Common prefixes: 'yougo', 'her01', etc.
                        if (speaker_prefix == b'yougo' or
                            speaker_prefix == b'her01' or
                            speaker_prefix == b'zara0' or
                            speaker_prefix == b'ness0' or
                            speaker_prefix == b'pear0' or
                            speaker_prefix == b'rich0' or
                            speaker_prefix == b'rath0' or
                            speaker_prefix == b'elza0' or
                            speaker_prefix == b'tiara'):
                            entry_offsets.append(i)

        # Remove duplicates and sort
        entry_offsets = sorted(set(entry_offsets))

        # Parse each entry
        for idx, offset in enumerate(entry_offsets):
            if offset + 8 > len(self.data):
                break

            # Read entry header (4 bytes): type (2) + index (2)
            entry_type = struct.unpack('<H', self.data[offset:offset+2])[0]
            entry_index = struct.unpack('<H', self.data[offset+2:offset+4])[0]

            # Determine next entry offset (or end of file)
            if idx + 1 < len(entry_offsets):
                next_offset = entry_offsets[idx + 1]
            else:
                next_offset = len(self.data)

            # Read speaker name (starts at offset + 4)
            speaker_offset = offset + 4
            speaker_data = self.data[speaker_offset:next_offset]

            # Find null terminator
            null_pos = speaker_data.find(b'\x00')
            if null_pos >= 0:
                speaker = speaker_data[:null_pos].decode('ascii', errors='replace')
                text_start = speaker_offset + null_pos + 1
            else:
                # No null found, check for padding
                speaker = speaker_data.rstrip(b'\xff').decode('ascii', errors='replace')
                text_start = speaker_offset + len(speaker) + 1

            # Read text data (from text_start to next entry)
            # Find ALL text fields within the entry (entries can have multiple text segments)
            text_segments = []

            search_pos = text_start
            while search_pos < next_offset:
                # Skip null/0xFF padding
                while search_pos < next_offset and self.data[search_pos] in (0x00, 0xFF):
                    search_pos += 1

                if search_pos >= next_offset:
                    break

                # Find the start of Japanese text (E3-E9 range) or ASCII text
                # Look for a continuous text segment until null or padding
                text_start_local = search_pos

                # Find end of this text segment
                text_end_local = text_start_local
                while text_end_local < next_offset:
                    byte_val = self.data[text_end_local]
                    if byte_val == 0x00 or byte_val == 0xFF:
                        break
                    text_end_local += 1

                # Extract the text segment
                if text_end_local > text_start_local + 1:
                    segment_bytes = self.data[text_start_local:text_end_local]

                    # Decode the segment
                    try:
                        segment_text = segment_bytes.decode('utf-8', errors='replace')
                        # Skip bytecode instructions and very short labels
                        if (len(segment_text) > 2 and
                            segment_text not in ('memory_init', 'memory_exit', 'COLLECTION_LINK',
                                              'scene_play', 'suma') and
                            not segment_text.startswith('@') and
                            not segment_text.startswith('#')):
                            text_segments.append(segment_text)
                    except:
                        pass

                search_pos = text_end_local + 1

            # Combine all text segments, separated by newlines
            # Usually the main dialogue is the longest segment
            if text_segments:
                # Sort by length (descending) - longest is usually the main dialogue
                text_segments.sort(key=len, reverse=True)
                # Use the longest segment as main text
                text = text_segments[0]
                # Append other segments as notes if they're meaningful
                notes = [s for s in text_segments[1:] if len(s) > 5]
                if notes:
                    text += ' [' + ', '.join(notes) + ']'
            else:
                text = ""

            # Only add entries with actual content
            if speaker or (text and len(text.strip()) > 0):
                entries.append({
                    'index': entry_index,
                    'type': entry_type,
                    'speaker': speaker,
                    'text': text
                })

        return entries

    def _find_code_start(self) -> int:
        """Find the CODE_START_ offset for parsing."""
        offset = 0x2C  # Skip header

        # Look for GLOBAL_DATA
        global_data_offset = self.data.find(b'GLOBAL_DATA')
        if global_data_offset > 0:
            offset = global_data_offset + 12  # Skip "GLOBAL_DATA" + 4 bytes

        # Look for CODE_START_
        code_start_offset = self.data.find(b'CODE_START_')
        if code_start_offset > 0:
            offset = code_start_offset + 12  # Skip "CODE_START_" + 4 bytes
            print(f"  Format: Full STCM2L (CODE_START_ at 0x{code_start_offset:X})", file=sys.stderr)

        return offset

    def _parse_padded_format(self) -> List[dict]:
        """
        Parse padded format entries (with 4-byte or 8-byte padding prefix).
        Pattern: 00 00 00 00 [00 00 00 00] TT TT TT 00 II II II 00 SS SS SS 00 [string data]
        v1.1.10: Added support for 8-byte padding (some Type 0x0A entries have 8 null bytes)
        NOTE: Scan entire file, not just from CODE_START_
        """
        entries = []
        # Start from beginning of file, not CODE_START_
        # The structured Type 2/4 entries may be anywhere in the file
        offset = 0

        pos = offset
        entry_count = 0
        type4_count = 0
        while pos < len(self.data) - 24:
            try:
                # Check for 4-byte padding (00 00 00 00)
                if self.data[pos] != 0x00 or self.data[pos+1] != 0x00 or self.data[pos+2] != 0x00 or self.data[pos+3] != 0x00:
                    pos += 1
                    continue

                # v1.1.10: Determine offset - check for 4 or 8 null bytes
                padding_offset = 4
                if (pos + 8 <= len(self.data) and
                    self.data[pos+4] == 0x00 and self.data[pos+5] == 0x00 and
                    self.data[pos+6] == 0x00 and self.data[pos+7] == 0x00):
                    # 8 null bytes found (some Type 0x0A entries have this padding)
                    padding_offset = 8

                # Read entry type at variable offset
                entry_type = struct.unpack('<I', self.data[pos+padding_offset:pos+padding_offset+4])[0]

                # Read index (4 bytes after type)
                entry_index = struct.unpack('<I', self.data[pos+padding_offset+4:pos+padding_offset+8])[0]

                # Read size (4 bytes after index)
                entry_size = struct.unpack('<I', self.data[pos+padding_offset+8:pos+padding_offset+12])[0]

                # Validate entry type (accept 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0F, 0x10, 0x11, 0x12)
                # 0x01: Choice options (English) (v1.1.13), 0x02/0x03: Choice options, 0x04: Main dialogue, 0x05/0x06: Dialogue continuation (v1.1.2), 0x07: Dialogue/narration, 0x08: Dialogue continuation (v1.1.10), 0x09: Dialogue (v1.1.11), 0x0A: Dialogue (v1.1.9), 0x0B/0x0C: Questions, 0x0F: Dialogue continuation (v1.1.15), 0x10: Dialogue continuation (v1.1.18), 0x11: Dialogue continuation (v1.1.19), 0x12: Narration
                if entry_type not in [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0F, 0x10, 0x11, 0x12]:
                    pos += 1
                    continue

                # v1.1.18: Type 0x10 has a placeholder size (0x4000), not actual text size
                if entry_type == 0x10:
                    # Calculate actual size by finding null terminator
                    text_start = pos + padding_offset + 12
                    text_end = text_start
                    while text_end < len(self.data) and text_end - text_start < 500:
                        if self.data[text_end] == 0x00:
                            # Check if followed by padding and next entry
                            null_count = 0
                            for i in range(4):
                                if text_end + i < len(self.data) and self.data[text_end + i] == 0x00:
                                    null_count += 1
                            if null_count >= 2:
                                break
                            text_end += 1
                        else:
                            text_end += 1
                    entry_size = text_end - text_start
                    if entry_size < 1:
                        pos += 1
                        continue
                else:
                    # Validate size (reasonable range)
                    if entry_size < 1 or entry_size > 10000:
                        pos += 1
                        continue

                # Validate index (reasonable range)
                if entry_index > 100000:
                    pos += 1
                    continue

                # Read string data (starts at byte 12 + padding_offset)
                string_end = pos + padding_offset + 12 + entry_size
                if string_end > len(self.data):
                    break

                string_data = self.data[pos+padding_offset+12:string_end]
                # Remove null padding from end
                text = string_data.rstrip(b'\x00').decode('utf-8', errors='replace')

                # Only add valid text entries (filter out garbage binary data)
                if text and self._is_valid_text(text):
                    entries.append({
                        'index': entry_index,
                        'type': entry_type,  # 0x02 for speaker names, 0x04 for dialogue
                        'text': text,
                        'size': entry_size,
                        'offset': pos  # v1.1.20: Track offset for unique identification
                    })
                    entry_count += 1
                    if entry_type == 4:
                        type4_count += 1

                # Move to next entry (aligned to next occurrence of pattern)
                pos = string_end

                # Skip padding bytes to find next entry
                while pos < len(self.data) - 24:
                    # Check for 4-byte or 8-byte padding + valid type
                    if (self.data[pos] == 0x00 and self.data[pos+1] == 0x00 and
                        self.data[pos+2] == 0x00 and self.data[pos+3] == 0x00):

                        # Determine offset for next entry check
                        check_offset = 4
                        next_type = struct.unpack('<I', self.data[pos+4:pos+8])[0]
                        next_size = struct.unpack('<I', self.data[pos+12:pos+16])[0]

                        # v1.1.10: Check for 8-byte padding
                        if (pos + 8 <= len(self.data) and
                            self.data[pos+4] == 0x00 and self.data[pos+5] == 0x00 and
                            self.data[pos+6] == 0x00 and self.data[pos+7] == 0x00):
                            # Has 8 null bytes, read the actual type at pos+8
                            check_offset = 8
                            next_type = struct.unpack('<I', self.data[pos+8:pos+12])[0]
                            next_size = struct.unpack('<I', self.data[pos+16:pos+20])[0]  # Size at pos+16 with 8-byte padding

                        # v1.1.9: Added 0x06, 0x0A to type list
                        # v1.1.10: Added 0x08 to type list
                        # v1.1.11: Added 0x09 to type list
                        # v1.1.13: Added 0x01 to type list
                        # v1.1.15: Added 0x0D, 0x0E to type list
                        # v1.1.18: Added 0x10 to type list
                        # v1.1.19: Added 0x11 to type list
                        if next_type in [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x10, 0x11]:
                            # v1.1.18: Type 0x10 has placeholder size (0x4000), skip size check
                            if next_type == 0x10 or 1 <= next_size <= 10000:
                                break
                    pos += 1

            except Exception as e:
                # If parsing fails, skip ahead
                pos += 1

        return entries

    def _parse_compact_format(self) -> List[dict]:
        """
        Parse compact format entries (without 4-byte padding).
        Pattern: TT TT TT 00 II II II 00 SS SS SS 00 [string data]
        Where TT = Type, II = Index, SS = Size

        Valid entry types: 0x02, 0x03, 0x04, 0x0B, 0x0C
        NOTE: Scan entire file, not just from CODE_START_
        """
        entries = []
        # Start from beginning of file, not CODE_START_
        # The structured Type entries may be anywhere in the file
        offset = 0

        pos = offset
        # v1.1.13: Fixed to allow processing entries at file end boundary (pos <= len(data) - 12)
        while pos + 12 <= len(self.data):
            try:
                # Read entry type (little-endian uint32)
                entry_type = struct.unpack('<I', self.data[pos:pos+4])[0]

                # Valid entry types are 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11, 0x12
                # 0x01: Choice options (English) (v1.1.13)
                # 0x05 and 0x07 are dialogue continuation types (v1.1.2)
                # 0x06 is also a dialogue type (v1.1.7)
                # 0x0A is a dialogue type (v1.1.9)
                # 0x0D, 0x0E are dialogue continuation types (v1.1.15)
                # 0x0F is dialogue continuation (v1.1.15)
                # 0x10 is dialogue continuation (v1.1.18) - size field is placeholder (0x4000), not actual size
                # 0x11 is dialogue continuation (v1.1.19)
                if entry_type not in [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11, 0x12]:
                    pos += 1
                    continue

                # Read index (bytes 4-7)
                entry_index = struct.unpack('<I', self.data[pos+4:pos+8])[0]

                # Validate index (reasonable range)
                if entry_index > 100000:
                    pos += 1
                    continue

                # Read size (bytes 8-11)
                entry_size = struct.unpack('<I', self.data[pos+8:pos+12])[0]

                # v1.1.18: Type 0x10 has a placeholder size (0x4000), not actual text size
                # Calculate actual size by finding null terminator or next entry
                if entry_type == 0x10:
                    # Skip the placeholder size and find actual text length
                    text_start = pos + 12
                    # Find null terminator or max 500 bytes
                    text_end = text_start
                    while text_end < len(self.data) and text_end - text_start < 500:
                        if self.data[text_end] == 0x00:
                            # Check if this is followed by more nulls (padding) and then a new entry
                            if text_end + 12 < len(self.data):
                                next_bytes = self.data[text_end:text_end+12]
                                # Valid entry header pattern: type not in valid range, check for structure
                                # Next entry starts with 4 null bytes, then type
                                null_count = 0
                                for i in range(4):
                                    if text_end + i < len(self.data) and self.data[text_end + i] == 0x00:
                                        null_count += 1
                                if null_count >= 2:
                                    break
                            text_end += 1
                        else:
                            text_end += 1
                    entry_size = text_end - text_start
                    if entry_size < 1:
                        pos += 1
                        continue
                else:
                    # Validate size (reasonable range)
                    # Filter out very small entries (likely bytecode) - minimum 4 bytes
                    if entry_size < 4 or entry_size > 10000:
                        pos += 1
                        continue

                # Read string data (starts at byte 12)
                string_end = pos + 12 + entry_size
                if string_end > len(self.data):
                    break

                string_data = self.data[pos+12:string_end]
                text = string_data.rstrip(b'\x00').decode('utf-8', errors='replace')

                if text and self._is_valid_text(text):
                    entries.append({
                        'index': entry_index,
                        'type': entry_type,
                        'text': text,
                        'size': entry_size,
                        'offset': pos  # v1.1.20: Track offset for unique identification
                    })

                pos = string_end
                # Skip padding
                while pos < len(self.data) - 16 and self.data[pos] == 0x00:
                    pos += 1

            except Exception as e:
                pos += 1

        return entries

    def _parse_legacy_utf8(self) -> List[dict]:
        """
        Legacy UTF-8 string extraction (fallback from v1.0.1).
        Scans for all valid UTF-8 strings in the data.
        Detects speaker names and marks them as Type 0x02.
        """
        entries = []
        offset = self._find_code_start()
        entry_count = 0

        # Scan for UTF-8 strings
        pos = offset
        while pos < len(self.data) - 4:
            try:
                # Look for start of UTF-8 string (E3-E9 for Japanese, or ASCII)
                byte_val = self.data[pos]

                # Skip null bytes and padding
                if byte_val == 0x00 or byte_val == 0xFF:
                    pos += 1
                    continue

                # Try to decode a UTF-8 string starting at this position
                text, bytes_consumed = self.decode_utf8_string(self.data, pos)

                if len(text) >= 2:  # Only keep strings with at least 2 characters
                    # Detect if this is a speaker name (Type 0x02) or dialogue (Type 0x04)
                    entry_type = 0x02 if self.is_speaker_name(text) else 0x04
                    entries.append({
                        'index': entry_count,
                        'type': entry_type,
                        'text': text,
                        'size': len(text.encode('utf-8'))
                    })
                    entry_count += 1
                    pos += bytes_consumed
                else:
                    pos += 1

            except Exception as e:
                pos += 1

        return entries

    def _is_valid_text(self, text: str) -> bool:
        """Check if text contains valid content (not just binary garbage or bytecode)."""
        if not text or len(text.strip()) < 2:
            return False

        # Check for Unicode replacement characters (indicates invalid UTF-8)
        # U+FFFD is the replacement character
        if '\ufffd' in text:
            return False

        # Check for control characters (except common ones like \n)
        control_count = sum(1 for c in text if ord(c) < 32 and c not in '\n\r\t')
        if control_count > len(text) / 4:  # More than 25% control chars
            return False

        # Quick check: if text starts with @ and is very short, it's likely bytecode
        if text.startswith('@') and len(text) < 5:
            return False

        # Check for binary garbage patterns
        # High ratio of @ symbols or control characters suggests binary data
        at_count = text.count('@')
        if len(text) > 10 and at_count > len(text) / 10:  # Much lower threshold: 10%
            return False

        # Check for bytecode/variable patterns (using word boundaries to avoid partial matches)
        import re
        bytecode_patterns = [
            r'\bRelease_', r'\bRute_count_', r'\bFav[A-Z]', r'\bLH_sel_', r'\bsure\d+',  # v1.1.20: Fixed to require digit after 'sure'
            r'\bsuma\b', r'\bmemory_', r'\bCOLLECTION_LINK', r'\bEXPORT_DATA', r'\bswitch',
            r'\bscene_play', r'\brathL', r'\belzaL', r'\bzara0', r'\bness0', r'\bher\d+',
            r'\bzk\d+', r'\bbg\d+',  # Bytecode variable patterns
            r'\b[A-Z][a-z]+_(bad|good)_end\b',  # Rath_bad_end, Arles_good_end, etc.
            r'\bTrueEnd\b',  # Route endings
            r'^[A-Z][a-z]+_[A-Za-z_]+$',  # Pattern like "Bad_PandR", "FavPearl" (full match)
            # Effect codes and UI elements (v1.0.3)
            r'\bef_[a-z0-9_]+\b',  # Effect codes (ef_shake5, ef_flash, etc.)
            r'\bselect\b',  # UI button text
            r'\bexport_data\b',  # Export markers (case insensitive)
            # Character variable patterns (v1.1.2)
            r'^[a-z]+\d+[a-z]*_[a-z]+$',  # raths01ht_kana, mejo07_kamae (lowercase+digits+optional letters+underscore)
            r'^[a-z]+\d+$',  # mejo07, rath02, etc. (lowercase with numbers, without underscore)
            r'^[a-z]{3,5}$',  # Short bytecode identifiers (cck, suma, etc.)
        ]
        text_stripped = text.strip()

        # Special case: Speaker names should always pass through (v1.1.2)
        # These are Type 0x02 entries that pair with dialogue entries
        if self.is_speaker_name(text_stripped):
            return True

        # v1.1.13: Known English UI choice words should pass through (from Type 0x01 entries)
        # These would otherwise be filtered out by the bytecode pattern check
        ENGLISH_CHOICE_WORDS = {'yes', 'no', 'ok', 'cancel', 'accept', 'decline', 'close'}
        if text_stripped.lower() in ENGLISH_CHOICE_WORDS:
            return True

        for pattern in bytecode_patterns:
            if re.search(pattern, text_stripped, re.IGNORECASE):
                # Only allow if it also has substantial Japanese content
                has_japanese = any(0x3040 <= ord(c) <= 0x9FFF for c in text)
                if not has_japanese:
                    return False

        # Check for meaningful content (Japanese, ASCII, or mixed)
        has_japanese = any(0x3040 <= ord(c) <= 0x9FFF for c in text)
        # v1.1.13: Changed from > 2 to >= 2 to allow "No" and other short English choice words
        has_english = sum(1 for c in text if c.isalpha()) >= 2

        return has_japanese or has_english

    def decompile_full_format(self) -> List[dict]:
        """
        Decompile the full STCM2L format (file 101 style).
        Uses both padded and compact format parsers, then merges results (v1.1.2).
        """
        # Try both parsers and merge the results
        padded_entries = self._parse_padded_format()
        compact_entries = self._parse_compact_format()

        # Combine entries, preferring compact format for overlapping indices
        # v1.1.7: Fixed to keep ALL entries, not just last one per index
        # v1.1.20: Fixed to track offsets to handle duplicate indices correctly
        entries = []
        compact_indices = set()

        # Add all compact entries first (they preserve original types better)
        for entry in compact_entries:
            entries.append(entry)
            compact_indices.add(entry['index'])

        # Add padded entries that don't overlap with compact entries (by index)
        for entry in padded_entries:
            if entry['index'] not in compact_indices:
                entries.append(entry)

        # Sort by index, then by offset to preserve file order for duplicate indices
        entries.sort(key=lambda e: (e['index'], e.get('offset', 0)))

        # Filter out bytecode identifiers and binary garbage
        entries = [e for e in entries if self._is_valid_text(e.get('text', ''))]

        # Process entries to handle speaker separation
        entries = self.combine_dialogue_entries(entries)

        return entries

    def decompile(self) -> List[dict]:
        """Main decompile function."""
        if not self.read_file():
            return []

        format_type = self.detect_format()
        print(f"Decompiling {self.filename} ({format_type} format)...", file=sys.stderr)

        if format_type == "dialogue":
            self.entries = self.decompile_dialogue_format()
        elif format_type == "full":
            self.entries = self.decompile_full_format()
        else:
            print(f"  Unknown format, attempting dialogue parse...", file=sys.stderr)
            self.entries = self.decompile_dialogue_format()

        return self.entries

    def format_text(self, text: str) -> str:
        """Format text for translation readability."""
        # Replace #n with newlines
        text = text.replace('#n', '\n')
        # Clean up extra whitespace
        text = re.sub(r'\n+', '\n', text)
        text = text.strip()
        return text

    def write_output(self, output_path: str):
        """Write decompiled output to file."""
        import shutil

        # v1.1.15: Remove existing directory if present (from nested folder bug)
        # When output_dir was a path like "decompiled_v1.1.15/40.txt",
        # previous versions created a directory at that path
        if os.path.isdir(output_path):
            shutil.rmtree(output_path)

        # Create parent directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"===================================================================\n")

            # Check if this is a choice dialogue format file
            is_choice_format = getattr(self, 'is_choice_format', False)

            if is_choice_format:
                f.write(f"STCM2L Decompiled Script - CHOICE DIALOGUE FORMAT\n")
            else:
                f.write(f"STCM2L Decompiled Script\n")

            f.write(f"Source: {self.filename}\n")
            f.write(f"===================================================================\n\n")

            # Add format-specific notes for choice dialogue
            if is_choice_format:
                f.write(f"NOTE: This file contains dialogue choices with voice/emotion variants.\n")
                f.write(f"Type 80 = Main dialogue choices\n")
                f.write(f"Type 82 = Alternative/short responses\n")
                f.write(f"Entries reference scene/event IDs (e.g., 64) rather than sequential numbers.\n")
                f.write(f"\n")

            if not self.entries:
                f.write("[No entries found]\n")
                return

            for entry in self.entries:
                speaker = entry.get('speaker', '')
                text = entry.get('text', '')
                entry_type = entry.get('type', 0)
                index = entry.get('index', 0)
                combined_from = entry.get('combined_from')

                # For choice format files, use sequential numbers instead of the reference ID
                # For other files, use the actual index from the binary
                is_choice_format = getattr(self, 'is_choice_format', False)
                is_choice = entry.get('is_choice', False)
                choice_tag = " [CHOICE]" if is_choice else ""

                if is_choice_format:
                    # Use a sequential counter for display
                    if not hasattr(self, '_entry_counter'):
                        self._entry_counter = 1
                    display_index = self._entry_counter
                    self._entry_counter += 1

                    # Show both sequential and reference ID
                    ref_id = f", RefID: {index}" if index != 64 else ""
                    f.write(f"--- Entry {display_index} (Type: {entry_type}{ref_id}){choice_tag} ---\n")
                else:
                    # v1.1.4: Use sequential display indices instead of binary Index field
                    # Most binary entries have Index=1, which is not useful for display
                    if not hasattr(self, '_display_index'):
                        self._display_index = 1
                    display_index = self._display_index
                    self._display_index += 1
                    f.write(f"--- Entry {display_index} (Type: {entry_type}){choice_tag} ---\n")

                # Show choice options count
                if is_choice and entry.get('choice_count', 0) > 1:
                    options = ' / '.join(entry.get('choice_options', []))
                    f.write(f"[{entry.get('choice_count')} options: {options}]\n")

                if speaker:
                    f.write(f"Speaker: {speaker}\n")

                formatted_text = self.format_text(text)
                if formatted_text:
                    f.write(f"Text:\n{formatted_text}\n")

                if combined_from:
                    f.write(f"[Combined from entries {combined_from}]\n")

                f.write("\n")

        print(f"  Wrote {len(self.entries)} entries to {output_path}", file=sys.stderr)


def decompile_file(input_path: str, output_dir: str) -> bool:
    """Decompile a single STCM2L file."""
    decompiler = STCM2LDecompiler(input_path)
    entries = decompiler.decompile()

    # Create output filename
    basename = os.path.basename(input_path)
    output_name = f"{basename}.txt"

    # v1.1.15: If output_dir already ends with .txt, use it directly (avoid nested folders)
    if output_dir.endswith('.txt'):
        output_path = output_dir
    else:
        output_path = os.path.join(output_dir, output_name)

    decompiler.write_output(output_path)
    return len(entries) > 0


def decompile_directory(input_dir: str, output_dir: str):
    """Decompile all STCM2L files in a directory."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)

    # Find all STCM2L files (files in SCRIPT folder are binary data)
    files = sorted(input_path.glob('*'), key=lambda p: p.name)

    # Filter out non-file entries
    files = [f for f in files if f.is_file()]

    print(f"Found {len(files)} files to decompile...", file=sys.stderr)

    success_count = 0
    for file in files:
        try:
            if decompile_file(str(file), str(output_path)):
                success_count += 1
        except Exception as e:
            print(f"Error processing {file.name}: {e}", file=sys.stderr)

    print(f"\nDecompilation complete: {success_count}/{len(files)} files processed", file=sys.stderr)


def main():
    # Handle --version flag
    if '--version' in sys.argv or '-v' in sys.argv:
        print(f"STCM2L Decompiler v{__version__}")
        sys.exit(0)

    if len(sys.argv) < 2:
        print("Usage: python stcm2l_decompiler.py <input_file_or_directory> [output_directory]")
        print("\nExamples:")
        print("  python stcm2l_decompiler.py SCRIPT/ decompiled/")
        print("  python stcm2l_decompiler.py SCRIPT/10")
        print("  python stcm2l_decompiler.py --version")
        sys.exit(1)

    input_path = sys.argv[1]

    if len(sys.argv) >= 3:
        output_dir = sys.argv[2]
    else:
        output_dir = OUTPUT_DIR

    if os.path.isfile(input_path):
        # Single file - use output_dir directly
        # v1.1.15: If output_dir ends with .txt, it's a file path, only create parent directory
        if output_dir.endswith('.txt'):
            parent_dir = os.path.dirname(output_dir)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
        else:
            os.makedirs(output_dir, exist_ok=True)
        decompile_file(input_path, output_dir)
    elif os.path.isdir(input_path):
        # Directory
        decompile_directory(input_path, output_dir)
    else:
        print(f"Error: {input_path} is not a valid file or directory", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
