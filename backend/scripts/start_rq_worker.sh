#!/bin/bash
# Wrapper script to start RQ worker with proper macOS configuration
# This ensures OBJC_DISABLE_INITIALIZE_FORK_SAFETY is set before Python starts

# Set the environment variable BEFORE Python starts
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

# Change to backend directory
cd "$(dirname "$0")/.."

# Run the Python script
python scripts/start_rq_worker.py
