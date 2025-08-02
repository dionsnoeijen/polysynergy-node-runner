#!/usr/bin/env python3
"""
Simple test runner script for the Polysynergy Node Runner project.
Usage: python run_tests.py [test_type]

Where test_type can be:
- unit: Run only unit tests
- integration: Run only integration tests
- aws: Run only AWS-dependent tests
- all: Run all tests (default)
"""
import sys
import subprocess

def run_command(cmd):
    """Run a command and return the exit code."""
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd).returncode

def main():
    test_type = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    base_cmd = ["poetry", "run", "pytest", "-v"]
    
    if test_type == "unit":
        cmd = base_cmd + ["tests/unit/", "-m", "unit"]
    elif test_type == "integration":
        cmd = base_cmd + ["tests/integration/", "-m", "integration"]
    elif test_type == "aws":
        cmd = base_cmd + ["-m", "aws"]
    elif test_type == "all":
        cmd = base_cmd
    elif test_type == "no-aws":
        cmd = base_cmd + ["-m", "not aws"]
    else:
        print(f"Unknown test type: {test_type}")
        print(__doc__)
        return 1
    
    return run_command(cmd)

if __name__ == "__main__":
    sys.exit(main())