from datetime import datetime
from collections import Counter
import json
import sys
from validation import validate_log_entry

VALID_LEVELS = {'DEBUG', 'INFO', 'WARN', 'ERROR'}

def execute_summary(log_entries):
    """
    Generate summary statistics from loaded logs.
    
    Args:
        log_entries: List of validated log entry dicts
        
    Returns:
        Dict with keys: total, event_types, levels, time_range
    """
    if not log_entries:
        return {
            'total': 0,
            'event_types': {},
            'levels': {},
            'time_range': {'earliest': None, 'latest': None}
        }

    event_type_counts = Counter()
    level_counts = Counter()

    for entry in log_entries:
        is_valid, error_message = validate_log_entry(entry)
        if not is_valid:
            continue
        if entry.get('event_type'):
            event_type_counts[entry['event_type']] += 1
        if entry.get('level'):
            level_counts[entry['level']] += 1
    
    time_range = {
        'earliest': log_entries[0].get('timestamp'),
        'latest': log_entries[-1].get('timestamp')
    }

    return {
        'total': len(log_entries),
        'event_types': dict(sorted(event_type_counts.items())),
        'levels': dict(sorted(level_counts.items())),
        'time_range': time_range
    }

def execute_filter(log_entries, level, start_time=None, end_time=None, event_type=None):
    """
    Filter log entries by level, optional time window, and optional event type.
    
    Args:
        log_entries: List of validated log entry dicts
        level: Level string to filter by
        start_time: Optional ISO timestamp string for start of window
        end_time: Optional ISO timestamp string for end of window
        event_type: Optional event type string to filter by
        
    Returns:
        List of filtered entries sorted by timestamp, then event_type
    """
    if level not in VALID_LEVELS:
        return []
    
    pre_filtered = []
    for entry in log_entries:
        is_valid, _ = validate_log_entry(entry)
        if not is_valid:
            continue
        if entry.get('level') != level:
            continue
        if event_type is not None and entry.get('event_type') != event_type:
            continue
        pre_filtered.append(entry)

    filtered = _apply_time_window_filter(pre_filtered, start_time, end_time)
    
    filtered.sort(key=lambda e: (e.get('timestamp', ''), e.get('event_type', '')))
    return filtered

def _apply_time_window_filter(log_entries, start_time=None, end_time=None):
    """Filter log entries to a specific time window, inclusively."""
    if start_time is None and end_time is None:
        return log_entries
    
    filtered_logs = []
    for entry in log_entries:
        if _is_within_time_window(entry.get('timestamp', ''), start_time, end_time):
            filtered_logs.append(entry)
    return filtered_logs

def _is_within_time_window(timestamp_str, start_time, end_time):
    """
    Check if timestamp falls within the specified time window.
    
    Args:
        timestamp_str: ISO timestamp string
        start_time: Optional ISO timestamp string for start
        end_time: Optional ISO timestamp string for end
        
    Returns:
        Boolean indicating if timestamp is within window
    """
    if not timestamp_str:
        return False
    try:
        ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return False
    if start_time is not None:
        try:
            start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            if ts < start:
                return False
        except (ValueError, AttributeError):
            return False
    if end_time is not None:
        try:
            end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            if ts > end:
                return False
        except (ValueError, AttributeError):
            return False
    return True

def execute_top(log_entries, n, event_type=None, group_by='event_type'):
    """
    Return top N most frequent messages grouped by the specified field.
    
    Args:
        log_entries: List of validated log entry dicts
        n: Integer number of top messages to return
        event_type: Optional event type string to filter by
        group_by: Field to group by ('event_type' or 'level')
        
    Returns:
        List of tuples (item, count) sorted by count desc, item asc
    """
    if not isinstance(n, int) or n <= 0:
        return []
    if not log_entries:
        return []
    
    filtered = []
    for entry in log_entries:
        is_valid, error_message = validate_log_entry(entry)
        if not is_valid:
            continue
        if event_type is not None and entry.get('event_type') != event_type:
            continue
        filtered.append(entry)
    
    counts = Counter()
    for entry in filtered:
        group_value = entry.get(group_by)
        if group_value:
            counts[group_value] += 1
    
    sorted_items = sorted(
        counts.items(),
        key=lambda x: (-x[1], x[0])
    )
    return sorted_items[:n]

def execute_export(logs, output_path, level=None, start_time=None, end_time=None, event_type=None):
    """
    Export filtered or full log entries to a JSON file with deterministic ordering.
    
    Args:
        logs: List of log entry dicts
        output_path: String path to output JSON file
        level: Optional level string to filter by
        start_time: Optional ISO timestamp string for start of window
        end_time: Optional ISO timestamp string for end of window
        event_type: Optional event type string to filter by
        
    Returns:
        True on success, False on failure.
    """
    if not logs:
        logs = []
    filtered = []
    for entry in logs:
        is_valid, error_message = validate_log_entry(entry)
        if not is_valid:
            continue
        if level is not None and entry.get('level') != level:
            continue
        if event_type is not None and entry.get('event_type') != event_type:
            continue
        if start_time is not None or end_time is not None:
            if not _is_within_time_window(entry.get('timestamp', ''), start_time, end_time):
                continue
        filtered.append(entry)
    filtered.sort(key=lambda e: (e.get('timestamp', ''), e.get('event_type', '')))
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(filtered, f, indent=2, sort_keys=True)
    except (IOError, OSError) as e:
        print(f"Error writing to output file {output_path}: {e}", file=sys.stderr)
        return False
    return True