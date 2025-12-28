#!/usr/bin/env python3
"""Example: connect Browser-Use to an existing Chrome profile.

Two safe options shown:
- Connect to an already-running Chrome/Edge with remote debugging (`cdp` mode).
- Let Browser-Use launch Chrome using your `user_data_dir` (`userdir` mode) — use with caution.

Usage examples (Windows):
  python connect_profile.py --mode cdp --cdp_url http://localhost:9222
  python connect_profile.py --mode userdir --user_data_dir "C:\\Users\\<you>\\AppData\\Local\\Google\\Chrome\\User Data\\Profile 1"
"""

import argparse
import asyncio
import os
from pathlib import Path

from browser_use import Browser


def default_windows_chrome_profile():
    return os.path.expandvars(r"%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default")


async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=("cdp", "userdir"), default="cdp", help="Connection mode")
    p.add_argument("--cdp_url", default="http://localhost:9222", help="CDP HTTP URL (e.g. http://localhost:9222)")
    p.add_argument("--user_data_dir", default=default_windows_chrome_profile(), help="Path to Chrome user data dir")
    p.add_argument("--executable_path", default=None, help="Path to Chrome/Edge executable (optional) for userdir mode")
    args = p.parse_args()

    if args.mode == "cdp":
        print(f"Connecting to running browser at {args.cdp_url} (make sure you started Chrome with --remote-debugging-port)")
        browser = Browser(cdp_url=args.cdp_url, headless=False)
    else:
        print(f"Launching Chrome using user_data_dir={args.user_data_dir} (DO NOT run your regular browser at the same time)")
        browser = Browser(user_data_dir=Path(args.user_data_dir), executable_path=args.executable_path, headless=False)

    try:
        await browser.start()

        # List open page targets
        targets = browser.session_manager.get_all_page_targets()
        print(f"Found {len(targets)} page targets:")
        for t in targets:
            print(" -", getattr(t, 'title', '<no title>'), getattr(t, 'url', '<no url>'))

        # Keep the session open briefly so you can see the browser
        await asyncio.sleep(1)

    finally:
        # Use stop() to disconnect and clear session state without killing the browser
        try:
            await browser.stop()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
