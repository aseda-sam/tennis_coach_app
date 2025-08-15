#!/usr/bin/env python3
"""
Simple runner for performance testing.
"""

import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from scripts.performance_test import main  # noqa: E402

if __name__ == "__main__":
    main()
