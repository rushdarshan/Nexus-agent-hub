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
from browser_use import Agent
from browser_use.llm import ChatGoogle
from browser_use.validators.aiml_validator import validate_choice


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


async def run_automation_task(task_description: str):
    """Run an agent for a general automation task."""
    print(f"\nRunning task: {task_description}\n")

    llm = ChatGoogle(model="gemini-2.0-flash", temperature=0.5)
    instructions = f"""
You are an autonomous browser automation agent.
USER REQUEST: {task_description}
Be explicit about actions taken and return a short structured summary.
"""

    try:
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


async def perform_click(url: str, selector: str):
    """Open url and click element matching selector."""
    print(f"\nClicking '{selector}' on {url}...\n")

    llm = ChatGoogle(model="gemini-2.0-flash", temperature=0.2)
    instructions = f"""
Open the page at: {url}
Find and click the element matching CSS selector: {selector}
If not found, try by text or ARIA role.
Describe what you clicked and any visible result.
"""

    try:
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


async def perform_scroll(url: str, amount: str):
    """Open url and scroll by amount (pixels or 'bottom')."""
    print(f"\nScrolling {url} by '{amount}'...\n")

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
    while True:
        print("\n=== MAIN MENU ===")
        print("1) New Automation Task")
        print("2) Click Element")
        print("3) Scroll Page")
        print("4) Exit")

        choice = input("\nSelect (1-4): ").strip()

        if choice == "1":
            intent = await get_user_intent()
            if intent:
                await run_automation_task(intent)

        elif choice == "2":
            url = input("Enter URL: ").strip()
            selector = input("Enter CSS selector to click: ").strip()
            if url and selector:
                await perform_click(url, selector)

        elif choice == "3":
            url = input("Enter URL: ").strip()
            amount = input("Scroll amount (pixels or 'bottom'): ").strip()
            if url and amount:
                await perform_scroll(url, amount)

        elif choice == "4":
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
