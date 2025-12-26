#!/usr/bin/env python3
"""
Quick start script for Autonomous Browser Automation.

Usage:
    python run_automation.py

This launches the interactive task runner where you can describe
any automation task and the system will execute it.
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set API key if not already set
if "GOOGLE_API_KEY" not in os.environ:
    print("\n⚠️  GOOGLE_API_KEY environment variable not set")
    print("   You can set it like this:")
    print("   export GOOGLE_API_KEY='your-key-here'")
    print("\n   Or paste your key now (or press Enter to skip):")
    api_key = input("   > ").strip()
    if api_key:
        os.environ["GOOGLE_API_KEY"] = api_key
    else:
        print("\n❌ API key required. Exiting.")
        sys.exit(1)

# Import and run
from browser_use.automation import main
import asyncio

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!\n")
        sys.exit(0)
