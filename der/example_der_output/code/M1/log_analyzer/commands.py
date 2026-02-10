import collections

def handle_summary(log_entries):
    """
    Calculates summary statistics for a list of log entries.

    Args:
        log_entries: An iterable of log entry dictionaries.

    Returns:
        A dictionary with total_entries, earliest_timestamp, and latest_timestamp.
    """
    if log_entries is None:
        return {
            'total_entries': 0,
            'earliest_timestamp': None,
            'latest_timestamp': None
        }

    entries = list(log_entries)

    if not entries:
        return {
            'total_entries': 0,
            'earliest_timestamp': None,
            'latest_timestamp': None
        }

    total_entries = len(entries)
    earliest_timestamp = None
    latest_timestamp = None

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        timestamp = entry.get('timestamp')
        if timestamp:
            if earliest_timestamp is None or timestamp < earliest_timestamp:
                earliest_timestamp = timestamp
            if latest_timestamp is None or timestamp > latest_timestamp:
                latest_timestamp = timestamp

    return {
        'total_entries': total_entries,
        'earliest_timestamp': earliest_timestamp,
        'latest_timestamp': latest_timestamp
    }


def handle_filter(log_entries, filter_criteria):
    """
    Filters log entries based on a set of criteria.

    Args:
        log_entries: An iterable of log entry dictionaries.
        filter_criteria: A dictionary of criteria to filter by.

    Returns:
        A list of log entries that match all criteria.
    """
    if log_entries is None:
        return []
    
    if not filter_criteria:
        return list(log_entries)

    filtered_entries = []
    for entry in log_entries:
        if not isinstance(entry, dict):
            continue
        if all(entry.get(key) == value for key, value in filter_criteria.items()):
            filtered_entries.append(entry)
            
    return filtered_entries


def handle_top(log_entries, field, n):
    """
    Finds the top N most frequent values for a specified field.

    Args:
        log_entries: An iterable of log entry dictionaries.
        field: The field name to analyze.
        n: The number of top values to return.

    Returns:
        A list of tuples (value, count) for the top N most frequent values.
    """
    if log_entries is None or not field or not isinstance(n, int) or n <= 0:
        return []

    values = (entry[field] for entry in log_entries if isinstance(entry, dict) and field in entry)
    counts = collections.Counter(values)

    # Sort by frequency (descending), then by value (ascending) for determinism.
    # This assumes that all values for the given field are of a comparable type.
    sorted_items = sorted(
        counts.items(), 
        key=lambda item: (-item[1], item[0])
    )

    return sorted_items[:n]