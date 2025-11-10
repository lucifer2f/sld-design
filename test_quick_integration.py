#!/usr/bin/env python3
"""
Simple wrapper for test_quick_integration.py to be used by CI system.
This script runs the quick integration test from the src folder.
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Run the quick integration test from the src folder."""
    test_path = Path("src") / "test_quick_integration.py"
    
    if not test_path.exists():
        print(f"Error: Test file {test_path} not found")
        sys.exit(1)
    
    try:
        result = subprocess.run([sys.executable, str(test_path)], cwd=".")
        sys.exit(result.returncode)
    except Exception as e:
        print(f"Error running test: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()