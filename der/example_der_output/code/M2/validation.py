"""Schema validation for JSONL log entries."""

from datetime import datetime

VALID_LEVELS = {"DEBUG", "INFO", "WARN", "ERROR"}
REQUIRED_FIELDS = {"timestamp", "event_type", "level", "message"}


def validate_log_entry(entry):
    """Validate a single JSONL log entry against required schema fields with strict type checking."""
    if not entry or not isinstance(entry, dict):
        return (False, "Log entry must be a non-empty dictionary")
    
    if not _has_required_fields(entry):
        return (False, "Missing required fields")
    
    if not _validate_timestamp(entry.get("timestamp")):
        return (False, "Invalid timestamp format")
    
    if not _validate_event_type(entry.get("event_type")):
        return (False, "event_type must be a non-empty string")
    
    if not _validate_level(entry.get("level")):
        return (False, f"level must be one of {VALID_LEVELS}")
    
    if not isinstance(entry.get("message"), str):
        return (False, "message must be a string")
    
    resource_id = entry.get("resourceId")
    if resource_id is not None and not isinstance(resource_id, str):
        return (False, "resourceId must be a string if present")
    
    return (True, None)


def _has_required_fields(entry):
    """Check that entry has required fields."""
    return REQUIRED_FIELDS.issubset(entry.keys())


def _validate_timestamp(timestamp):
    """Validate timestamp is ISO 8601 format string."""
    if not timestamp or not isinstance(timestamp, str):
        return False
    
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return True
    except (ValueError, AttributeError):
        return False


def _validate_event_type(event_type):
    """Validate event_type is non-empty string."""
    if not event_type or not isinstance(event_type, str):
        return False
    return len(event_type.strip()) > 0


def _validate_level(level):
    """Validate level is one of: DEBUG, INFO, WARN, ERROR."""
    if not level or not isinstance(level, str):
        return False
    return level in VALID_LEVELS