"""JSONL log file loading and parsing."""

import json
import sys
from validation import validate_log_entry


def load_jsonl_logs(file_path):
    """Load and parse JSONL file line-by-line with validation and deterministic ordering by timestamp."""
    if not file_path:
        return []
    
    entries = _read_and_parse_lines(file_path)
    valid_entries = _filter_valid_entries(entries)
    sorted_entries = _sort_by_timestamp(valid_entries)
    
    for entry in sorted_entries:
        if '_line_num' in entry:
            del entry['_line_num']
    
    return sorted_entries


def _read_and_parse_lines(file_path):
    """Read file line-by-line and parse JSON."""
    entries = []
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    parsed = _parse_json_line(line, line_num)
                    if parsed is not None:
                        parsed['_line_num'] = line_num
                        entries.append(parsed)
                except ValueError as e:
                    print(f"Warning: Malformed JSON at line {line_num}", file=sys.stderr)
    except (IOError, OSError) as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        return []
    
    return entries


def _parse_json_line(line, line_num):
    """Parse and validate a single JSON line with error handling."""
    try:
        entry = json.loads(line)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

    is_valid, error_message = validate_log_entry(entry)
    if not is_valid:
        print(f"Error: Invalid log entry on line {line_num}: {error_message}", file=sys.stderr)
        return None
    
    return entry


def _filter_valid_entries(entries):
    """Filter entries using validation module."""
    valid = []
    for entry in entries:
        result = validate_log_entry(entry)
        if isinstance(result, tuple):
            is_valid, _ = result
            if is_valid:
                valid.append(entry)
        elif result:
            valid.append(entry)
    return valid


def _sort_by_timestamp(entries):
    """Sort entries by timestamp ascending with deterministic secondary key for identical timestamps."""
    if not entries:
        return []
    
    try:
        return sorted(
            entries,
            key=lambda e: (
                e.get("timestamp", ""),
                e.get("_line_num", 0)
            )
        )
    except (TypeError, KeyError):
        return entries