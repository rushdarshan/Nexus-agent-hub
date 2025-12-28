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
from dotenv import load_dotenv
load_dotenv()

if "GOOGLE_API_KEY" not in os.environ and "BROWSER_USE_API_KEY" not in os.environ:
    print("\n⚠️  No API key found in environment variables (GOOGLE_API_KEY or BROWSER_USE_API_KEY)")
    print("   Please create a .env file or export the variable.")
    print("\n   Enter your Gemini/Google API key to continue (or press Enter to exit):")
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
