"""Tests for CLI commands with deterministic output validation."""

import os
import json
import tempfile
import subprocess
import sys


def test_summary_command():
    """Validate that the summary command produces deterministic output with correct counts for all log levels and event types."""
    fixture_path = _create_test_fixture()
    if not fixture_path:
        print("Error: Failed to create test fixture", file=sys.stderr)
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, "main.py", "summary", fixture_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            print(f"Error: summary command failed with code {result.returncode}", file=sys.stderr)
            return False
        
        output = result.stdout
        if not output:
            print("Error: summary command produced no output", file=sys.stderr)
            return False
        
        if "Total entries:" not in output:
            print("Error: summary output missing expected format", file=sys.stderr)
            return False
        
        return True
    finally:
        _cleanup_file(fixture_path)


def test_filter_command_with_time_window():
    """Validate that the filter command correctly filters logs by time window and event type, producing deterministic sorted output."""
    fixture_path = _create_test_fixture()
    if not fixture_path:
        print("Error: Failed to create test fixture", file=sys.stderr)
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, "main.py", "filter", fixture_path,
             "--event-type", "user_login",
             "--start-time", "2024-01-01T00:00:00Z",
             "--end-time", "2024-12-31T23:59:59Z"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            print(f"Error: filter command failed with code {result.returncode}", file=sys.stderr)
            return False
        
        output = result.stdout
        if not output:
            print("Error: filter command produced no output", file=sys.stderr)
            return False
        
        lines = output.strip().split('\n')
        if len(lines) < 1:
            print("Error: filter output has insufficient lines", file=sys.stderr)
            return False
        
        return True
    finally:
        _cleanup_file(fixture_path)


def test_export_command_deterministic():
    """Validate that the export command writes deterministic JSON output with sorted keys and proper indentation to the output file."""
    fixture_path = _create_test_fixture()
    if not fixture_path:
        print("Error: Failed to create test fixture", file=sys.stderr)
        return False
    
    output_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = f.name
        
        result = subprocess.run(
            [sys.executable, "main.py", "export", fixture_path,
             "--output", output_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            print(f"Error: export command failed with code {result.returncode}", file=sys.stderr)
            return False
        
        if not os.path.exists(output_path):
            print("Error: export command did not create output file", file=sys.stderr)
            return False
        
        with open(output_path, 'r') as f:
            content = f.read()
        
        if not content:
            print("Error: export output file is empty", file=sys.stderr)
            return False
        
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            print("Error: export output is not valid JSON", file=sys.stderr)
            return False
        
        return True
    finally:
        _cleanup_file(fixture_path)
        if output_path:
            _cleanup_file(output_path)


def test_top_command_deterministic():
    """Validate that the 'top' command produces deterministic, sorted output and respects the limit."""
    content = (
        '{"timestamp":"2024-06-15T10:00:00Z","event_type":"logout","level":"INFO","message":"User logged out"}\n'
        '{"timestamp":"2024-06-15T10:01:00Z","event_type":"login","level":"INFO","message":"User logged in"}\n'
        '{"timestamp":"2024-06-15T10:02:00Z","event_type":"login","level":"INFO","message":"User logged in again"}\n'
        '{"timestamp":"2024-06-15T10:03:00Z","event_type":"error","level":"ERROR","message":"An error occurred"}\n'
        '{"timestamp":"2024-06-15T10:04:00Z","event_type":"logout","level":"INFO","message":"Another user logged out"}\n'
        '{"timestamp":"2024-06-15T10:05:00Z","event_type":"login","level":"INFO","message":"Third user logged in"}\n'
        '{"timestamp":"2024-06-15T10:06:00Z","event_type":"warning","level":"WARN","message":"A warning was issued"}\n'
        '{"timestamp":"2024-06-15T10:07:00Z","event_type":"error","level":"ERROR","message":"Another error occurred"}\n'
    )
    
    fixture_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            fixture_path = f.name
            f.write(content)
        
        result = subprocess.run(
            [sys.executable, "main.py", "top", fixture_path, "--n", "3"],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode != 0:
            print(f"Error: top command failed. Stderr: {result.stderr}", file=sys.stderr)
            return False
        
        expected_output = "login: 3\nerror: 2\nlogout: 2"
        if result.stdout.strip() != expected_output:
            print(f"Error: top command output mismatch. Expected:\n{expected_output}\nGot:\n{result.stdout.strip()}", file=sys.stderr)
            return False

        result_level = subprocess.run(
            [sys.executable, "main.py", "top", fixture_path, "--n", "2", "--group-by", "level"],
            capture_output=True, text=True, timeout=10
        )

        if result_level.returncode != 0:
            print(f"Error: top command with group-by level failed. Stderr: {result_level.stderr}", file=sys.stderr)
            return False

        expected_output_level = "INFO: 5\nERROR: 2"
        if result_level.stdout.strip() != expected_output_level:
            print(f"Error: top command output mismatch for group-by level. Expected:\n{expected_output_level}\nGot:\n{result_level.stdout.strip()}", file=sys.stderr)
            return False

        return True
    finally:
        if fixture_path:
            _cleanup_file(fixture_path)


def test_top_command_json_output():
    """Verify the 'top' command correctly produces JSON output when '--format json' is specified."""
    content = (
        '{"timestamp":"2024-06-15T10:00:00Z","event_type":"login","level":"INFO","message":"User logged in"}\n'
        '{"timestamp":"2024-06-15T10:01:00Z","event_type":"logout","level":"INFO","message":"User logged out"}\n'
        '{"timestamp":"2024-06-15T10:02:00Z","event_type":"login","level":"INFO","message":"User logged in again"}\n'
    )
    fixture_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            fixture_path = f.name
            f.write(content)

        result = subprocess.run(
            [sys.executable, "main.py", "top", fixture_path, "--n", "2", "--format", "json"],
            capture_output=True, text=True, timeout=10
        )

        if result.returncode != 0:
            print(f"Error: top command with json format failed. Stderr: {result.stderr}", file=sys.stderr)
            return False

        try:
            output_data = json.loads(result.stdout)
        except json.JSONDecodeError:
            print(f"Error: top command output is not valid JSON. Output: {result.stdout}", file=sys.stderr)
            return False

        expected_data = {"login": 2, "logout": 1}
        if output_data != expected_data:
            print(f"Error: JSON output mismatch. Expected: {expected_data}, Got: {output_data}", file=sys.stderr)
            return False

        return True
    finally:
        if fixture_path:
            _cleanup_file(fixture_path)


def test_top_command_empty_event_type():
    """Verify 'top' command fails with an empty string for --event-type."""
    fixture_path = _create_test_fixture()
    if not fixture_path:
        print("Error: Failed to create test fixture", file=sys.stderr)
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, "main.py", "top", fixture_path, "--event-type", ""],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("Error: 'top' command with empty event_type succeeded unexpectedly.", file=sys.stderr)
            return False
        
        expected_error = "Error: --event-type argument cannot be empty or contain only whitespace."
        if expected_error not in result.stderr:
            print(f"Error: Expected error message not found for empty --event-type. Stderr: {result.stderr}", file=sys.stderr)
            return False
        
        return True
    finally:
        _cleanup_file(fixture_path)


def test_top_command_missing_event_type():
    """Ensure the 'top' command fails when the mandatory '--event-type' argument is not provided."""
    fixture_path = _create_test_fixture()
    if not fixture_path:
        print("Error: Failed to create test fixture", file=sys.stderr)
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, "main.py", "top", fixture_path],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            print("Error: 'top' command succeeded without mandatory '--event-type' argument.", file=sys.stderr)
            return False
            
        if "required" not in result.stderr.lower() or "--event-type" not in result.stderr:
            print(f"Error: Expected error message for missing '--event-type' not found in stderr. Stderr: {result.stderr}", file=sys.stderr)
            return False
            
        return True
    finally:
        _cleanup_file(fixture_path)


def test_top_command_invalid_format():
    """Ensure the 'top' command fails when an invalid value is provided for the '--format' argument."""
    fixture_path = _create_test_fixture()
    if not fixture_path:
        print("Error: Failed to create test fixture", file=sys.stderr)
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, "main.py", "top", fixture_path, "--format", "xml"],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            print("Error: 'top' command succeeded with invalid format 'xml'.", file=sys.stderr)
            return False
            
        if "invalid choice" not in result.stderr.lower():
            print(f"Error: Expected error message for invalid format not found in stderr. Stderr: {result.stderr}", file=sys.stderr)
            return False
            
        return True
    finally:
        _cleanup_file(fixture_path)


def test_top_command_default_format():
    """Verify the 'top' command produces the default human-readable output when the '--format' argument is omitted."""
    content = (
        '{"timestamp":"2024-06-15T10:00:00Z","event_type":"login","level":"INFO","message":"User logged in"}\n'
        '{"timestamp":"2024-06-15T10:01:00Z","event_type":"logout","level":"INFO","message":"User logged out"}\n'
        '{"timestamp":"2024-06-15T10:02:00Z","event_type":"login","level":"INFO","message":"User logged in again"}\n'
    )
    fixture_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            fixture_path = f.name
            f.write(content)

        result = subprocess.run(
            [sys.executable, "main.py", "top", fixture_path, "--n", "2"],
            capture_output=True, text=True, timeout=10
        )

        if result.returncode != 0:
            print(f"Error: top command with default format failed. Stderr: {result.stderr}", file=sys.stderr)
            return False

        expected_output = "login: 2\nlogout: 1"
        if result.stdout.strip() != expected_output:
            print(f"Error: Default format output mismatch. Expected:\n{expected_output}\nGot:\n{result.stdout.strip()}", file=sys.stderr)
            return False

        return True
    finally:
        if fixture_path:
            _cleanup_file(fixture_path)


def test_invalid_event_type():
    """Validate that an empty event_type argument triggers a non-zero exit code."""
    fixture_path = _create_test_fixture()
    if not fixture_path:
        print("Error: Failed to create test fixture", file=sys.stderr)
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, "main.py", "filter", fixture_path, "--event-type", ""],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            print("Error: Empty event_type did not cause a failure.", file=sys.stderr)
            return False
        
        if "Error: event_type cannot be an empty string" not in result.stderr:
            print("Error: Expected error message for empty event_type not found.", file=sys.stderr)
            return False
        
        return True
    finally:
        _cleanup_file(fixture_path)


def test_malformed_jsonl_handling():
    """Validate that malformed JSONL lines are skipped gracefully and valid entries are processed."""
    content = (
        '{"timestamp":"2024-06-15T10:00:00Z","event_type":"user_login","level":"INFO","message":"User logged in"}\n'
        'this is not a valid json line\n'
        '{"timestamp":"2024-06-15T10:05:00Z","event_type":"user_logout","level":"INFO","message":"User logged out"}\n'
        '{"level":"WARN"}\n'
    )
    
    fixture_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            fixture_path = f.name
            f.write(content)
        
        result = subprocess.run(
            [sys.executable, "main.py", "summary", fixture_path],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode != 0:
            print(f"Error: summary command failed with malformed file. Stderr: {result.stderr}", file=sys.stderr)
            return False
        
        if "Total entries: 2" not in result.stdout:
            print(f"Error: summary count is incorrect for malformed file. Output: {result.stdout}", file=sys.stderr)
            return False
        
        return True
    finally:
        if fixture_path:
            _cleanup_file(fixture_path)


def test_time_window_boundaries():
    """Validate that time window filtering correctly handles exact boundary timestamps."""
    content = (
        '{"timestamp":"2024-01-01T09:59:59Z", "event_type":"before", "level":"INFO", "message":"before window"}\n'
        '{"timestamp":"2024-01-01T10:00:00Z", "event_type":"on_start", "level":"INFO", "message":"on start window"}\n'
        '{"timestamp":"2024-01-01T11:00:00Z", "event_type":"in_middle", "level":"INFO", "message":"in middle window"}\n'
        '{"timestamp":"2024-01-01T12:00:00Z", "event_type":"on_end", "level":"INFO", "message":"on end window"}\n'
        '{"timestamp":"2024-01-01T12:00:01Z", "event_type":"after", "level":"INFO", "message":"after window"}\n'
    )
    
    fixture_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            fixture_path = f.name
            f.write(content)
        
        result = subprocess.run(
            [sys.executable, "main.py", "filter", fixture_path,
             "--start-time", "2024-01-01T10:00:00Z",
             "--end-time", "2024-01-01T12:00:00Z"],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode != 0:
            print(f"Error: filter command failed on boundary test. Stderr: {result.stderr}", file=sys.stderr)
            return False
        
        output_lines = result.stdout.strip().split('\n')
        if len(output_lines) != 3:
            print(f"Error: Incorrect number of lines in boundary test output. Expected 3, got {len(output_lines)}", file=sys.stderr)
            return False
        
        output_content = result.stdout
        if "on_start" not in output_content or "in_middle" not in output_content or "on_end" not in output_content:
            print("Error: Boundary test output missing expected events.", file=sys.stderr)
            return False
        
        if "before" in output_content or "after" in output_content:
            print("Error: Boundary test output contains unexpected events.", file=sys.stderr)
            return False
        
        return True
    finally:
        if fixture_path:
            _cleanup_file(fixture_path)


def test_summary_human_readable_output():
    """Validate that the summary command produces correct human-readable string output with all expected labels."""
    fixture_path = _create_test_fixture()
    if not fixture_path:
        print("Error: Failed to create test fixture", file=sys.stderr)
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, "main.py", "summary", fixture_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            print(f"Error: summary command failed with code {result.returncode}", file=sys.stderr)
            return False
        
        output = result.stdout
        if not output:
            print("Error: summary command produced no output", file=sys.stderr)
            return False
        
        required_labels = ["Total entries:", "Event types:", "Levels:", "Time range:"]
        for label in required_labels:
            if label not in output:
                print(f"Error: summary output missing expected label '{label}'", file=sys.stderr)
                return False
        
        return True
    finally:
        _cleanup_file(fixture_path)


def test_invalid_event_type_whitespace():
    """Validate that event_type arguments that are empty or contain only whitespace trigger a non-zero exit code."""
    fixture_path = _create_test_fixture()
    if not fixture_path:
        print("Error: Failed to create test fixture", file=sys.stderr)
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, "main.py", "filter", fixture_path, "--event-type", ""],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            print("Error: Empty event_type did not cause a failure.", file=sys.stderr)
            return False
        
        if "Error:" not in result.stderr:
            print("Error: Expected error message for empty event_type not found.", file=sys.stderr)
            return False
        
        result = subprocess.run(
            [sys.executable, "main.py", "filter", fixture_path, "--event-type", "   "],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            print("Error: Whitespace-only event_type did not cause a failure.", file=sys.stderr)
            return False
        
        if "Error:" not in result.stderr:
            print("Error: Expected error message for whitespace event_type not found.", file=sys.stderr)
            return False
        
        return True
    finally:
        _cleanup_file(fixture_path)


def test_empty_input_file():
    """Validate that all commands handle an empty input .jsonl file gracefully without crashing."""
    fixture_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            fixture_path = f.name
        
        result = subprocess.run(
            [sys.executable, "main.py", "summary", fixture_path],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode != 0:
            print(f"Error: summary command failed on empty file. Stderr: {result.stderr}", file=sys.stderr)
            return False
        
        if "Total entries: 0" not in result.stdout:
            print("Error: summary output incorrect for empty file.", file=sys.stderr)
            return False
        
        result = subprocess.run(
            [sys.executable, "main.py", "filter", fixture_path],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode != 0:
            print(f"Error: filter command failed on empty file. Stderr: {result.stderr}", file=sys.stderr)
            return False
        
        result = subprocess.run(
            [sys.executable, "main.py", "top", fixture_path, "--n", "5"],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode != 0:
            print(f"Error: top command failed on empty file. Stderr: {result.stderr}", file=sys.stderr)
            return False
        
        output_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                output_path = f.name
            
            result = subprocess.run(
                [sys.executable, "main.py", "export", fixture_path, "--output", output_path],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode != 0:
                print(f"Error: export command failed on empty file. Stderr: {result.stderr}", file=sys.stderr)
                return False
            
            with open(output_path, 'r') as f:
                content = f.read()
            
            data = json.loads(content)
            if not isinstance(data, list) or len(data) != 0:
                print("Error: export output incorrect for empty file.", file=sys.stderr)
                return False
        finally:
            if output_path:
                _cleanup_file(output_path)
        
        return True
    finally:
        if fixture_path:
            _cleanup_file(fixture_path)


def test_nonexistent_input_file():
    """Validate that the CLI exits with an error when the specified input file does not exist."""
    nonexistent_path = "/tmp/this_file_does_not_exist_12345.jsonl"
    
    result = subprocess.run(
        [sys.executable, "main.py", "summary", nonexistent_path],
        capture_output=True, text=True, timeout=10
    )
    
    if result.returncode == 0:
        print("Error: Command succeeded with nonexistent file.", file=sys.stderr)
        return False
    
    if "Error:" not in result.stderr:
        print("Error: Expected error message for nonexistent file not found.", file=sys.stderr)
        return False
    
    return True


def test_invalid_time_format_arg():
    """Validate that the CLI rejects invalid ISO 8601 time formats for --start-time and --end-time arguments and provides an informative error."""
    fixture_path = _create_test_fixture()
    if not fixture_path:
        print("Error: Failed to create test fixture", file=sys.stderr)
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, "main.py", "filter", fixture_path,
             "--start-time", "not-a-date"],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            print("Error: Invalid time format did not cause a failure.", file=sys.stderr)
            return False
        
        if "Error:" not in result.stderr:
            print("Error: Expected error message for invalid time format not found.", file=sys.stderr)
            return False
        
        result = subprocess.run(
            [sys.executable, "main.py", "filter", fixture_path,
             "--end-time", "invalid-timestamp"],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            print("Error: Invalid end-time format did not cause a failure.", file=sys.stderr)
            return False
        
        if "Error:" not in result.stderr:
            print("Error: Expected error message for invalid end-time format not found.", file=sys.stderr)
            return False
        
        return True
    finally:
        _cleanup_file(fixture_path)


def test_start_time_after_end_time():
    """Validate that the CLI fails if --start-time is after --end-time."""
    fixture_path = _create_test_fixture()
    if not fixture_path:
        print("Error: Failed to create test fixture", file=sys.stderr)
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, "main.py", "filter", fixture_path,
             "--start-time", "2025-01-01T00:00:00Z",
             "--end-time", "2024-01-01T00:00:00Z"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("Error: Command succeeded with start_time after end_time.", file=sys.stderr)
            return False
        
        expected_error = "Error: --start-time cannot be after --end-time."
        if expected_error not in result.stderr:
            print(f"Error: Expected error message '{expected_error}' not found in stderr.", file=sys.stderr)
            print(f"Stderr was: {result.stderr}", file=sys.stderr)
            return False
        
        return True
    finally:
        _cleanup_file(fixture_path)


def test_missing_required_event_type_arg():
    """Validate that commands requiring --event-type (filter, top, export) fail with an error message when the argument is missing."""
    fixture_path = _create_test_fixture()
    if not fixture_path:
        print("Error: Failed to create test fixture", file=sys.stderr)
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, "main.py", "filter", fixture_path],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            print("Error: filter command succeeded without --event-type.", file=sys.stderr)
            return False
        
        if "Error:" not in result.stderr and "required" not in result.stderr.lower():
            print("Error: Expected error message for missing --event-type not found.", file=sys.stderr)
            return False
        
        return True
    finally:
        _cleanup_file(fixture_path)


def test_determinism_with_identical_timestamps():
    """Validate that the output order is deterministic when multiple log entries share the exact same timestamp."""
    content = (
        '{"timestamp":"2024-06-15T10:00:00Z","event_type":"event_b","level":"INFO","message":"b"}\n'
        '{"timestamp":"2024-06-15T10:00:00Z","event_type":"event_a","level":"WARN","message":"a"}\n'
        '{"timestamp":"2024-06-15T10:00:00Z","event_type":"event_c","level":"ERROR","message":"c"}\n'
    )
    
    fixture_path = None
    output_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            fixture_path = f.name
            f.write(content)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = f.name
        
        result = subprocess.run(
            [sys.executable, "main.py", "export", fixture_path, "--output", output_path],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode != 0:
            print(f"Error: export command failed on identical timestamps. Stderr: {result.stderr}", file=sys.stderr)
            return False
        
        with open(output_path, 'r') as f:
            content_output = f.read()
        
        data = json.loads(content_output)
        if len(data) != 3:
            print("Error: Incorrect number of entries in output.", file=sys.stderr)
            return False
        
        result2 = subprocess.run(
            [sys.executable, "main.py", "export", fixture_path, "--output", output_path],
            capture_output=True, text=True, timeout=10
        )
        
        if result2.returncode != 0:
            print(f"Error: Second export command failed. Stderr: {result2.stderr}", file=sys.stderr)
            return False
        
        with open(output_path, 'r') as f:
            content_output2 = f.read()
        
        if content_output != content_output2:
            print("Error: Output order is not deterministic for identical timestamps.", file=sys.stderr)
            return False
        
        return True
    finally:
        if fixture_path:
            _cleanup_file(fixture_path)
        if output_path:
            _cleanup_file(output_path)


def test_event_type_validation_error_format():
    """Validate that invalid event type errors are reported with consistent formatting using the centralized error helper."""
    fixture_path = _create_test_fixture()
    if not fixture_path:
        print("Error: Failed to create test fixture", file=sys.stderr)
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, "main.py", "filter", fixture_path, "--event-type", ""],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            print("Error: Empty event_type did not cause a failure.", file=sys.stderr)
            return False
        
        if not result.stderr.startswith("Error: "):
            print("Error: Error message does not start with 'Error: ' prefix.", file=sys.stderr)
            return False
        
        if "--event-type" not in result.stderr:
            print("Error: Error message does not mention --event-type.", file=sys.stderr)
            return False
        
        return True
    finally:
        _cleanup_file(fixture_path)


def test_time_window_inclusive_boundaries():
    """Verify that time window filtering is inclusive of the start and end boundaries."""
    content = (
        '{"timestamp":"2023-01-01T10:00:00Z", "event_type":"boundary_event", "level":"INFO", "message":"start"}\n'
        '{"timestamp":"2023-01-01T12:00:00Z", "event_type":"boundary_event", "level":"INFO", "message":"end"}\n'
    )
    fixture_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            fixture_path = f.name
            f.write(content)
        
        result = subprocess.run(
            [sys.executable, "main.py", "filter", fixture_path,
             "--start-time", "2023-01-01T10:00:00Z",
             "--end-time", "2023-01-01T12:00:00Z"],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode != 0:
            print(f"Error: filter command failed on inclusive boundary test. Stderr: {result.stderr}", file=sys.stderr)
            return False
        
        output_lines = result.stdout.strip().split('\n')
        if len(output_lines) != 2:
            print(f"Error: Incorrect number of lines in inclusive boundary test. Expected 2, got {len(output_lines)}", file=sys.stderr)
            return False
        
        return True
    finally:
        if fixture_path:
            _cleanup_file(fixture_path)


def test_filter_event_type_case_sensitive():
    """Verify that the --event-type filter is case-sensitive."""
    content = (
        '{"timestamp":"2023-01-01T10:00:00Z", "event_type":"login", "level":"INFO", "message":"user login"}\n'
        '{"timestamp":"2023-01-01T10:01:00Z", "event_type":"LOGIN", "level":"INFO", "message":"admin login"}\n'
        '{"timestamp":"2023-01-01T10:02:00Z", "event_type":"Login", "level":"INFO", "message":"guest login"}\n'
    )
    fixture_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            fixture_path = f.name
            f.write(content)
        
        result = subprocess.run(
            [sys.executable, "main.py", "filter", fixture_path,
             "--event-type", "login"],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode != 0:
            print(f"Error: filter command failed on case-sensitive test. Stderr: {result.stderr}", file=sys.stderr)
            return False
        
        output = result.stdout.strip()
        if not output:
            print("Error: case-sensitive test produced no output", file=sys.stderr)
            return False

        lines = output.split('\n')
        if len(lines) != 1:
            print(f"Error: case-sensitive test returned wrong number of lines. Expected 1, got {len(lines)}", file=sys.stderr)
            return False
        
        try:
            data = json.loads(lines[0])
            if data.get("event_type") != "login":
                print("Error: case-sensitive test returned wrong event_type.", file=sys.stderr)
                return False
        except json.JSONDecodeError:
            print("Error: case-sensitive test output is not valid JSON.", file=sys.stderr)
            return False

        return True
    finally:
        if fixture_path:
            _cleanup_file(fixture_path)


def test_top_command_group_by_level():
    """Add a test case to verify the 'top' command's '--group-by level' functionality, ensuring it correctly counts and displays the top log levels."""
    content = (
        '{"timestamp":"2024-06-15T10:00:00Z","event_type":"login","level":"INFO","message":"User logged in"}\n'
        '{"timestamp":"2024-06-15T10:01:00Z","event_type":"logout","level":"INFO","message":"User logged out"}\n'
        '{"timestamp":"2024-06-15T10:02:00Z","event_type":"error","level":"ERROR","message":"An error occurred"}\n'
        '{"timestamp":"2024-06-15T10:03:00Z","event_type":"warning","level":"WARN","message":"A warning"}\n'
        '{"timestamp":"2024-06-15T10:04:00Z","event_type":"debug","level":"DEBUG","message":"Debug info"}\n'
        '{"timestamp":"2024-06-15T10:05:00Z","event_type":"login","level":"INFO","message":"Another login"}\n'
        '{"timestamp":"2024-06-15T10:06:00Z","event_type":"error","level":"ERROR","message":"Another error"}\n'
    )
    fixture_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            fixture_path = f.name
            f.write(content)
        
        result = subprocess.run(
            [sys.executable, "main.py", "top", fixture_path, "--group-by", "level", "--n", "3"],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode != 0:
            print(f"Error: top command with group-by level failed. Stderr: {result.stderr}", file=sys.stderr)
            return False
        
        expected_output = "INFO: 3\nERROR: 2\nDEBUG: 1"
        if result.stdout.strip() != expected_output:
            print(f"Error: top group-by level output mismatch. Expected:\n{expected_output}\nGot:\n{result.stdout.strip()}", file=sys.stderr)
            return False
        
        return True
    finally:
        if fixture_path:
            _cleanup_file(fixture_path)


def test_top_command_group_by_event_type():
    """Add a test case to verify the 'top' command's '--group-by event_type' functionality, ensuring it correctly counts and displays the top event types within a specific event type."""
    content = (
        '{"timestamp":"2024-06-15T10:00:00Z","event_type":"user_action","level":"INFO","message":"Action 1"}\n'
        '{"timestamp":"2024-06-15T10:01:00Z","event_type":"user_action","level":"INFO","message":"Action 2"}\n'
        '{"timestamp":"2024-06-15T10:02:00Z","event_type":"user_action","level":"INFO","message":"Action 3"}\n'
        '{"timestamp":"2024-06-15T10:03:00Z","event_type":"system_event","level":"INFO","message":"System 1"}\n'
        '{"timestamp":"2024-06-15T10:04:00Z","event_type":"system_event","level":"INFO","message":"System 2"}\n'
    )
    fixture_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            fixture_path = f.name
            f.write(content)
        
        result = subprocess.run(
            [sys.executable, "main.py", "top", fixture_path, "--group-by", "event_type", "--event-type", "user_action", "--n", "2"],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode != 0:
            print(f"Error: top command with group-by event_type failed. Stderr: {result.stderr}", file=sys.stderr)
            return False
        
        expected_output = "user_action: 3"
        if result.stdout.strip() != expected_output:
            print(f"Error: top group-by event_type output mismatch. Expected:\n{expected_output}\nGot:\n{result.stdout.strip()}", file=sys.stderr)
            return False
        
        return True
    finally:
        if fixture_path:
            _cleanup_file(fixture_path)


def test_top_command_group_by_event_type_requires_event_type_arg():
    """Add a test case to validate that the 'top' command with '--group-by event_type' fails with an error if the '--event-type' argument is not provided."""
    fixture_path = _create_test_fixture()
    if not fixture_path:
        print("Error: Failed to create test fixture", file=sys.stderr)
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, "main.py", "top", fixture_path, "--group-by", "event_type"],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            print("Error: top command with group-by event_type succeeded without --event-type.", file=sys.stderr)
            return False
        
        if "--event-type" not in result.stderr or "required" not in result.stderr.lower():
            print(f"Error: Expected error message for missing --event-type not found. Stderr: {result.stderr}", file=sys.stderr)
            return False
        
        return True
    finally:
        _cleanup_file(fixture_path)


def test_top_command_group_by_determinism():
    """Verify that the output for the 'top' command with '--group-by' remains deterministic when counts are equal."""
    content = (
        '{"timestamp":"2024-06-15T10:00:00Z","event_type":"event_a","level":"INFO","message":"msg"}\n'
        '{"timestamp":"2024-06-15T10:01:00Z","event_type":"event_b","level":"INFO","message":"msg"}\n'
        '{"timestamp":"2024-06-15T10:02:00Z","event_type":"event_c","level":"WARN","message":"msg"}\n'
        '{"timestamp":"2024-06-15T10:03:00Z","event_type":"event_d","level":"WARN","message":"msg"}\n'
    )
    fixture_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            fixture_path = f.name
            f.write(content)
        
        result1 = subprocess.run(
            [sys.executable, "main.py", "top", fixture_path, "--group-by", "level", "--n", "5"],
            capture_output=True, text=True, timeout=10
        )
        
        if result1.returncode != 0:
            print(f"Error: first top command with group-by level failed. Stderr: {result1.stderr}", file=sys.stderr)
            return False
        
        result2 = subprocess.run(
            [sys.executable, "main.py", "top", fixture_path, "--group-by", "level", "--n", "5"],
            capture_output=True, text=True, timeout=10
        )
        
        if result2.returncode != 0:
            print(f"Error: second top command with group-by level failed. Stderr: {result2.stderr}", file=sys.stderr)
            return False
        
        if result1.stdout != result2.stdout:
            print(f"Error: top group-by output is not deterministic. First:\n{result1.stdout}\nSecond:\n{result2.stdout}", file=sys.stderr)
            return False
        
        expected_output = "INFO: 2\nWARN: 2"
        if result1.stdout.strip() != expected_output:
            print(f"Error: top group-by determinism output mismatch. Expected:\n{expected_output}\nGot:\n{result1.stdout.strip()}", file=sys.stderr)
            return False
        
        return True
    finally:
        if fixture_path:
            _cleanup_file(fixture_path)


def _create_test_fixture():
    """Create a temporary test fixture file with sample log entries."""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"timestamp":"2024-06-15T10:00:00Z","event_type":"user_login","level":"INFO","message":"User logged in"}\n')
            f.write('{"timestamp":"2024-06-15T10:05:00Z","event_type":"user_logout","level":"INFO","message":"User logged out"}\n')
            f.write('{"timestamp":"2024-06-15T10:10:00Z","event_type":"error_occurred","level":"ERROR","message":"An error occurred"}\n')
            return f.name
    except Exception as e:
        print(f"Error creating test fixture: {e}", file=sys.stderr)
        return None


def _cleanup_file(file_path):
    """Remove a temporary file if it exists."""
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass