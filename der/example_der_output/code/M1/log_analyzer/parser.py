import json

def validate_log_entry(entry):
    """
    Validate a single log entry object against a predefined schema.

    A valid entry must be a dictionary containing 'timestamp', 'level',
    and 'message' keys, all with string values.

    Args:
        entry: A dictionary representing a single log entry.

    Returns:
        True if the entry is valid, False otherwise.
    """
    if not isinstance(entry, dict):
        return False
    
    required_keys = {"timestamp", "level", "message"}
    if not required_keys.issubset(entry.keys()):
        return False

    if not all(isinstance(entry[key], str) for key in required_keys):
        return False
        
    return True

def parse_log_file(file_path):
    """
    Read a .jsonl log file, parse and validate each line, and return a sorted list of valid log entries.

    This function gracefully handles file-not-found errors and skips lines
    that are empty, contain invalid JSON, or fail schema validation.

    Args:
        file_path: The path to the .jsonl log file.

    Returns:
        A list of valid log entry dictionaries, sorted by timestamp.
    """
    valid_entries = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    log_entry = json.loads(line)
                    if validate_log_entry(log_entry):
                        valid_entries.append(log_entry)
                except json.JSONDecodeError:
                    # Skip lines that are not valid JSON
                    continue
    except FileNotFoundError:
        print(f"Error: File not found at '{file_path}'")
        return []

    valid_entries.sort(key=lambda entry: entry['timestamp'])
    return valid_entries