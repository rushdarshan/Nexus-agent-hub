"""
AUTONOMOUS BROWSER AUTOMATION - Interactive Task Runner

Provides:
- Interactive menu for natural-language tasks
- Click Element action
- Scroll Page action
- Integration with Agent + ChatGoogle LLM
- Secondary validation via validate_choice
"""

import asyncio

from browser_use import Agent, BrowserProfile
from browser_use.llm import ChatGoogle
from browser_use.validators.aiml_validator import validate_choice
import platform
import shlex
import subprocess

try:
    import winreg
except Exception:
    winreg = None


# Browser executable paths for Windows (Chromium-based browsers only)
# Note: browser-use uses CDP (Chrome DevTools Protocol), so only Chromium-based browsers work
BROWSER_EXECUTABLES = {
    "comet": r"C:\Users\rushd\AppData\Local\Perplexity\Comet\Application\comet.exe",
    "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "brave": r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
}


def get_browser_executable(browser: str) -> str | None:
    """Get the executable path for a browser name."""
    return BROWSER_EXECUTABLES.get(browser.lower())


def get_browser_choice():
    """Prompt user to select which browser to use.
    
    Note: Only Chromium-based browsers are supported (CDP required).
    Firefox/LibreWolf are NOT supported by browser-use framework.
    """
    print("\n=== SELECT BROWSER ===")
    print("(Only Chromium-based browsers supported)")
    print("1) Comet (default)")
    print("2) Edge")
    print("3) Chrome")
    print("4) Brave")
    print("5) Other (use system default)")

    choice = input("\nSelect browser (1-5, default 1): ").strip()

    browser_map = {
        "1": "comet",
        "2": "edge",
        "3": "chrome",
        "4": "brave",
        "5": "system",
    }

    return browser_map.get(choice, "comet")


def detect_system_default_browser_executable() -> str | None:
    """Detect the system default browser executable path.

    Returns an executable path or None if detection failed.
    Supports Windows (registry), macOS and Linux heuristics.
    """
    plat = platform.system().lower()
    try:
        if plat == "windows" and winreg is not None:
            # Try HKEY_CLASSES_ROOT\http\shell\open\command
            try:
                with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"http\shell\open\command") as key:
                    cmd, _ = winreg.QueryValueEx(key, None)
                    # command may contain args, extract executable
                    exe = shlex.split(cmd, posix=False)[0].strip('"')
                    return exe
            except Exception:
                # Fallback: user choice mapping
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice") as key:
                        progid, _ = winreg.QueryValueEx(key, 'ProgId')
                        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, progid + r"\shell\open\command") as k2:
                            cmd, _ = winreg.QueryValueEx(k2, None)
                            exe = shlex.split(cmd, posix=False)[0].strip('"')
                            return exe
                except Exception:
                    return None

        if plat == "darwin":
            # macOS: use 'defaults' to get the default handler for http
            try:
                out = subprocess.check_output(["/usr/bin/defaults", "read", "com.apple.LaunchServices/com.apple.launchservices.secure", "LSHandlers"], stderr=subprocess.DEVNULL)
                # parsing LSHandlers is complex; prefer 'open' fallback
            except Exception:
                pass
            return None

        # Linux: try xdg-settings
        if plat == "linux":
            try:
                out = subprocess.check_output(["xdg-settings", "get", "default-web-browser"], stderr=subprocess.DEVNULL, text=True).strip()
                # returns something like 'com.brave.Browser.desktop'
                desktop = out
                # try to resolve .desktop file to Exec
                try:
                    desktop_file = f"/usr/share/applications/{desktop}"
                    with open(desktop_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.startswith('Exec='):
                                parts = line.split('=', 1)[1].strip().split()
                                exe = parts[0]
                                return exe
                except Exception:
                    return None
            except Exception:
                return None

    except Exception:
        return None

    return None


async def get_user_intent():
    """Prompt the user for a natural-language automation request."""
    print("\n=== AUTONOMOUS BROWSER AUTOMATION ===\n")
    print("Examples:")
    print("  - Find top 3 ergonomic mice under $100 on Amazon")
    print("  - Compare iPhone 15 prices across stores")
    print("  - Fill this Google Form with my details")
    print("  - Check if laptop price dropped below $1200\n")

    intent = input("What would you like me to automate?\n> ").strip()
    if not intent:
        print("No task specified.")
        return None
    return intent


async def run_automation_task(task_description: str, browser: str):
    """Run an agent for a general automation task."""
    print(f"\nRunning task on {browser.upper()}: {task_description}\n")

    llm = ChatGoogle(model="gemini-2.0-flash", temperature=0.5)
    instructions = f"""
You are an autonomous browser automation agent.
USER REQUEST: {task_description}
Be explicit about actions taken and return a short structured summary.
"""

    try:
        if browser == "system":
            # Attempt to detect the system default browser executable and pass
            # it explicitly so the agent launches the user's preferred browser
            exe = detect_system_default_browser_executable()
            if exe:
                browser_config = BrowserProfile(executable_path=exe)
                agent = Agent(task=instructions, llm=llm, browser_profile=browser_config)
            else:
                # Last resort: no profile (may fall back to Edge/Chromium)
                agent = Agent(task=instructions, llm=llm)
        else:
            # Use executable path for known browsers
            exe = get_browser_executable(browser)
            if exe:
                browser_config = BrowserProfile(executable_path=exe)
                agent = Agent(task=instructions, llm=llm, browser_profile=browser_config)
            else:
                agent = Agent(task=instructions, llm=llm)
        result = await agent.run(max_steps=20)

        print("\n--- RESULT ---\n")
        if getattr(result, "final_result", None):
            print(result.final_result)
            try:
                validation = validate_choice(str(result.final_result))
                print("\nValidator:", validation)
            except Exception:
                print("\nValidator unavailable.")
        else:
            print("Task executed (no textual summary).")
        return True
    except Exception as e:
        print(f"Automation error: {e}")
        return False


async def perform_click(url: str, selector: str, browser: str):
    """Open url and click element matching selector."""
    print(f"\nClicking '{selector}' on {url} using {browser.upper()}...\n")

    llm = ChatGoogle(model="gemini-2.0-flash", temperature=0.2)
    instructions = f"""
Open the page at: {url}
Find and click the element matching CSS selector: {selector}
If not found, try by text or ARIA role.
Describe what you clicked and any visible result.
"""

    try:
        if browser == "system":
            exe = detect_system_default_browser_executable()
            if exe:
                browser_config = BrowserProfile(executable_path=exe)
                agent = Agent(task=instructions, llm=llm, browser_profile=browser_config)
            else:
                agent = Agent(task=instructions, llm=llm)
        else:
            # Use executable path for known browsers
            exe = get_browser_executable(browser)
            if exe:
                browser_config = BrowserProfile(executable_path=exe)
                agent = Agent(task=instructions, llm=llm, browser_profile=browser_config)
            else:
                agent = Agent(task=instructions, llm=llm)
        result = await agent.run(max_steps=12)
        print("\n--- CLICK RESULT ---\n")
        if getattr(result, "final_result", None):
            print(result.final_result)
            try:
                validation = validate_choice(str(result.final_result))
                print("\nValidator:", validation)
            except Exception:
                print("\nValidator unavailable.")
        else:
            print("Click completed (no textual result).")
    except Exception as e:
        print(f"Click failed: {e}")


async def perform_scroll(url: str, amount: str, browser: str):
    """Open url and scroll by amount (pixels or 'bottom')."""
    print(f"\nScrolling {url} by '{amount}' using {browser.upper()}...\n")

    llm = ChatGoogle(model="gemini-2.0-flash", temperature=0.2)

    parsed = amount.strip().lower()
    if parsed == "bottom":
        scroll_instruction = "Scroll to the bottom of the page and report any new content loaded."
    else:
        try:
            pixels = int(parsed)
            scroll_instruction = f"Scroll down by {pixels} pixels and report any visible changes."
        except ValueError:
            scroll_instruction = f"Scroll down by '{amount}' and report any visible changes."

    instructions = f"""
Open the page at: {url}
{scroll_instruction}
Describe what changed after scrolling.
"""

    try:
        if browser == "system":
            exe = detect_system_default_browser_executable()
            if exe:
                browser_config = BrowserProfile(executable_path=exe)
                agent = Agent(task=instructions, llm=llm, browser_profile=browser_config)
            else:
                agent = Agent(task=instructions, llm=llm)
        else:
            # Use executable path for known browsers
            exe = get_browser_executable(browser)
            if exe:
                browser_config = BrowserProfile(executable_path=exe)
                agent = Agent(task=instructions, llm=llm, browser_profile=browser_config)
            else:
                agent = Agent(task=instructions, llm=llm)
        result = await agent.run(max_steps=12)
        print("\n--- SCROLL RESULT ---\n")
        if getattr(result, "final_result", None):
            print(result.final_result)
            try:
                validation = validate_choice(str(result.final_result))
                print("\nValidator:", validation)
            except Exception:
                print("\nValidator unavailable.")
        else:
            print("Scroll completed (no textual result).")
    except Exception as e:
        print(f"Scroll failed: {e}")


async def interactive_menu():
    """Main interactive menu."""
    # Ask for browser selection once at the start
    browser = get_browser_choice()
    
    while True:
        print("\n=== MAIN MENU ===")
        print(f"(Using: {browser.upper()})")
        print("1) New Automation Task")
        print("2) Click Element")
        print("3) Scroll Page")
        print("4) Change Browser")
        print("5) Exit")

        choice = input("\nSelect (1-5): ").strip()

        if choice == "1":
            intent = await get_user_intent()
            if intent:
                await run_automation_task(intent, browser)

        elif choice == "2":
            url = input("Enter URL: ").strip()
            selector = input("Enter CSS selector to click: ").strip()
            if url and selector:
                await perform_click(url, selector, browser)

        elif choice == "3":
            url = input("Enter URL: ").strip()
            amount = input("Scroll amount (pixels or 'bottom'): ").strip()
            if url and amount:
                await perform_scroll(url, amount, browser)

        elif choice == "4":
            browser = get_browser_choice()
            print(f"✓ Browser changed to {browser.upper()}")

        elif choice == "5":
            print("Goodbye!")
            break

        else:
            print("Invalid option.")


async def main():
    print("\nStarting Automation CLI...")
    await interactive_menu()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted. Goodbye!")
