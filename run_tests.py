#!/usr/bin/env python3
"""
Test runner script for the electrical design application.
This script runs tests from the src folder and provides a unified interface.
"""

import sys
import os
import subprocess
from pathlib import Path

def run_test(test_name):
    """Run a specific test file from the src directory."""
    test_path = Path("src") / test_name
    if not test_path.exists():
        print(f"Error: Test file {test_path} not found")
        return False
    
    try:
        result = subprocess.run([sys.executable, str(test_path)], 
                              capture_output=True, text=True, cwd=".")
        print(f"Running {test_name}...")
        if result.stdout:
            print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {test_name} passed")
            return True
        else:
            print(f"❌ {test_name} failed with exit code {result.returncode}")
            return False
    except Exception as e:
        print(f"Error running {test_name}: {e}")
        return False

def main():
    """Main test runner function."""
    if len(sys.argv) < 2:
        print("Usage: python run_tests.py <test_name>")
        print("Available tests:")
        test_files = list(Path("src").glob("test_*.py"))
        for test_file in test_files:
            print(f"  - {test_file.name}")
        sys.exit(1)
    
    test_name = sys.argv[1]
    if not test_name.startswith("test_"):
        test_name = f"test_{test_name}"
    if not test_name.endswith(".py"):
        test_name = f"{test_name}.py"
    
    success = run_test(test_name)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()