"""Output formatting functions for log_analyzer CLI."""

import json


def format_summary_output(summary):
    """
    Formats summary data into a human-readable string.

    Args:
        summary (dict): A dictionary containing summary data with keys
                        'total', 'event_types', 'levels', and 'time_range'.

    Returns:
        str: A multi-line, human-readable string with summary statistics.
    """
    if not summary:
        return "Total entries: 0\nEvent types: \nLevels: \nTime Range: N/A"

    total = summary.get('total', 0)
    event_types = sorted(summary.get('event_types', []))
    levels = sorted(summary.get('levels', []))
    time_range = summary.get('time_range', {})

    event_types_str = ", ".join(event_types)
    levels_str = ", ".join(levels)
    
    earliest = time_range.get('earliest')
    latest = time_range.get('latest')
    
    if earliest is None:
        time_range_str = "N/A"
    else:
        time_range_str = f"{earliest} - {latest}"

    return (
        f"Total entries: {total}\n"
        f"Event types: {event_types_str}\n"
        f"Levels: {levels_str}\n"
        f"Time Range: {time_range_str}"
    )


def format_filter_output(log_entries):
    """
    Formats a list of log entries into a JSONL string.

    Each line is a JSON object with sorted keys for deterministic output.

    Args:
        log_entries (list): A list of log entry dictionaries.

    Returns:
        str: A string with each JSON log entry on a new line.
    """
    if not log_entries:
        return ""
    
    lines = [json.dumps(entry, sort_keys=True) for entry in log_entries]
    return "\n".join(lines)


def format_top_output(top_data, format_type):
    """
    Format a list of top items into a deterministic output string.

    Args:
        top_data: A list of tuples (item, count).
        format_type: Output format, either 'text' or 'json'.

    Returns:
        A string with formatted output, or an empty string if input is empty.
    """
    if not top_data:
        if format_type == "json":
            return "{}"
        return ""

    if format_type == "json":
        json_dict = {item: count for item, count in top_data}
        return json.dumps(json_dict, sort_keys=True, indent=2)

    lines = []
    for item, count in top_data:
        lines.append(f"{item}: {count}")
    
    return "\n".join(lines)


def format_export_output(log_entries):
    """
    Formats a list of log entries into an indented JSON array string.

    Keys for each log entry object are sorted for deterministic output.

    Args:
        log_entries (list): A list of log entry dictionaries.

    Returns:
        str: A string representing a valid, indented JSON array.
    """
    if not log_entries:
        return "[]"
    
    return json.dumps(log_entries, sort_keys=True, indent=2)