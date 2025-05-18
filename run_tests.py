import os
import subprocess
import sys
import time
from datetime import datetime

def print_header(message):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f" {message} ".center(80, "="))
    print("=" * 80)

def run_command(command, description):
    """Run a command and print its output."""
    print_header(description)
    print(f"Running: {command}")
    start_time = time.time()
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    duration = time.time() - start_time
    
    print(f"Command completed in {duration:.2f} seconds with exit code {result.returncode}")
    
    if result.stdout:
        print("\nSTDOUT:")
        print(result.stdout)
    
    if result.stderr:
        print("\nSTDERR:")
        print(result.stderr)
    
    return result.returncode == 0

def main():
    """Run all tests for Phase 4 tasks."""
    os.environ["FLASK_ENV"] = "testing"
    
    print_header("AgroMap Uzbekistan - Phase 4 Testing")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create a list of test tasks
    test_tasks = [
        ("Security Tests", "pytest tests/test_security.py -v"),
        ("Load Tests", "pytest tests/test_load.py -v"),
        ("Feature Tests", "pytest tests/test_features.py -v"),
        ("Region Detection Tests", "pytest tests/test_region_detection.py -v"),
        ("Sample Tests", "pytest tests/test_sample.py -v"),
    ]
    
    # Run each test task
    results = {}
    for description, command in test_tasks:
        success = run_command(command, description)
        results[description] = "PASSED" if success else "FAILED"
    
    # Print summary
    print_header("Test Summary")
    for description, status in results.items():
        print(f"{description}: {status}")
    
    # Check if any tests failed
    if "FAILED" in results.values():
        print("\nSome tests failed. Please review the output above for details.")
        return 1
    else:
        print("\nAll tests passed successfully!")
        return 0

if __name__ == "__main__":
    sys.exit(main())