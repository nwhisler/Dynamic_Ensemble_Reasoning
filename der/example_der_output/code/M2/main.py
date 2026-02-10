#!/usr/bin/env python3
"""CLI entry point for log_analyzer tool."""

import argparse
import sys
import os
from datetime import datetime
from loader import load_jsonl_logs
from commands import execute_summary, execute_filter, execute_top, execute_export
from output import format_summary_output, format_filter_output, format_top_output, format_export_output


def main():
    """Parse CLI arguments for commands summary, filter, top, and export with required input file path and optional parameters."""
    parser = argparse.ArgumentParser(
        prog="log_analyzer",
        description="Analyze JSONL event logs with deterministic output"
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")
    
    summary_parser = subparsers.add_parser("summary", help="Generate summary statistics")
    summary_parser.add_argument("input", help="Path to input JSONL log file")
    
    filter_parser = subparsers.add_parser("filter", help="Filter logs by criteria")
    filter_parser.add_argument("input", help="Path to input JSONL log file")
    filter_parser.add_argument("--level", help="Filter by log level")
    filter_parser.add_argument("--event-type", help="Filter by event type")
    filter_parser.add_argument("--start-time", help="Filter start time (ISO 8601)")
    filter_parser.add_argument("--end-time", help="Filter end time (ISO 8601)")
    
    top_parser = subparsers.add_parser("top", help="Show top N events")
    top_parser.add_argument("input", help="Path to input JSONL log file")
    top_parser.add_argument("--n", type=int, default=10, help="Number of top events")
    top_parser.add_argument("--event-type", help="Filter by event type")
    top_parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format (text or json)")
    top_parser.add_argument("--group-by", choices=["event_type", "level"], default="event_type", help="Group by event_type or level")
    
    export_parser = subparsers.add_parser("export", help="Export filtered logs to JSON")
    export_parser.add_argument("input", help="Path to input JSONL log file")
    export_parser.add_argument("--output", required=True, help="Output JSON file path")
    export_parser.add_argument("--level", help="Filter by log level")
    export_parser.add_argument("--event-type", help="Filter by event type")
    export_parser.add_argument("--start-time", help="Filter start time (ISO 8601)")
    export_parser.add_argument("--end-time", help="Filter end time (ISO 8601)")
    
    args = parser.parse_args()
    
    if not _validate_args(args):
        return 1
    
    _validate_input_file(args.input)

    _validate_time_args(
        getattr(args, 'start_time', None),
        getattr(args, 'end_time', None)
    )
    
    _validate_event_type_arg(args.command, getattr(args, 'event_type', None))

    if hasattr(args, 'format'):
        _validate_format_arg(args.format)
    
    result = dispatch_command(args)
    if result is None:
        return 1
    
    return 0


def _exit_with_error(message):
    """Print a formatted error message to stderr and exit."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def _validate_args(args):
    """Validate that arguments are provided and command-specific constraints are met."""
    if args.command == 'top':
        group_by = getattr(args, 'group_by', 'event_type')
        event_type = getattr(args, 'event_type', None)
        if group_by == 'event_type' and event_type is None:
            _exit_with_error("--event-type is required when grouping by 'event_type' in the 'top' command")
    return True


def _validate_input_file(file_path):
    """Validate that input file exists."""
    if not file_path:
        _exit_with_error("Input file path is required")
    
    if not os.path.exists(file_path):
        _exit_with_error(f"Input file does not exist: {file_path}")
    
    if not os.path.isfile(file_path):
        _exit_with_error(f"Input path is not a file: {file_path}")
    
    return True

def _validate_time_args(start_time, end_time):
    """Validate that time arguments are in valid ISO 8601 format and logical."""
    start_dt = None
    end_dt = None
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        except ValueError:
            _exit_with_error(f"Invalid --start-time format: '{start_time}'. Use ISO 8601.")
    
    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        except ValueError:
            _exit_with_error(f"Invalid --end-time format: '{end_time}'. Use ISO 8601.")

    if start_dt and end_dt and start_dt > end_dt:
        _exit_with_error("--start-time cannot be after --end-time.")


def _validate_event_type_arg(command, event_type):
    """Validate that the event_type argument provided via CLI is a non-empty string when present."""
    if event_type is None:
        return
    if not event_type or not event_type.strip():
        _exit_with_error("--event-type argument cannot be empty or contain only whitespace.")


def _validate_format_arg(format_value):
    """Validate that the --format argument is either 'text' or 'json'."""
    if format_value not in ['text', 'json']:
        _exit_with_error(f"Invalid --format value: '{format_value}'. Must be 'text' or 'json'.")
    return format_value


def dispatch_command(args):
    """
    Route validated CLI arguments to the appropriate command function.
    
    Args:
        args: Parsed argparse namespace with command and parameters
        
    Returns:
        True on success, None on failure.
    """
    try:
        log_entries = load_jsonl_logs(args.input)
    except Exception as e:
        _exit_with_error(f"loading logs: {e}")

    if args.command == "summary":
        result = execute_summary(log_entries)
        print(format_summary_output(result))
    elif args.command == "filter":
        level = getattr(args, 'level', None)
        event_type = getattr(args, 'event_type', None)
        start_time = getattr(args, 'start_time', None)
        end_time = getattr(args, 'end_time', None)
        result = execute_filter(
            log_entries,
            level=level,
            event_type=event_type,
            start_time=start_time,
            end_time=end_time
        )
        print(format_filter_output(result))
    elif args.command == "top":
        n = getattr(args, 'n', 10)
        event_type = getattr(args, 'event_type', None)
        format_type = getattr(args, 'format', 'text')
        group_by = getattr(args, 'group_by', 'event_type')
        result = execute_top(log_entries, n, event_type, group_by)
        print(format_top_output(result, format_type))
    elif args.command == "export":
        output_path = args.output
        level = getattr(args, 'level', None)
        event_type = getattr(args, 'event_type', None)
        start_time = getattr(args, 'start_time', None)
        end_time = getattr(args, 'end_time', None)
        success = execute_export(
            log_entries,
            output_path,
            level=level,
            event_type=event_type,
            start_time=start_time,
            end_time=end_time
        )
        if not success:
            return None
    else:
        _exit_with_error(f"Unknown command: {args.command}")

    return True


if __name__ == "__main__":
    sys.exit(main())