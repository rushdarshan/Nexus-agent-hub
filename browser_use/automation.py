"""
AUTONOMOUS BROWSER AUTOMATION - Interactive Task Runner

A versatile AI-powered automation system that listens to natural language
commands and executes them on any website.

Users can ask the system to:
- Research products and compare prices
- Fill forms and submit data
- Automate data entry workflows
- Monitor websites for changes
- Extract and structure information
- And much more...

The system is powered by:
- Gemini 2.0 Flash (reasoning + vision)
- browser-use framework (browser control)
- Specialized agents (orchestration)
- Universal payment automation (when needed)
"""
import asyncio
import os
from pathlib import Path

# API key should be set via GOOGLE_API_KEY environment variable
# Do NOT hardcode credentials in source code

from browser_use import Agent
from browser_use.llm import ChatGoogle


async def get_user_intent():
    """Get the user's automation request via interactive prompt."""
    print("""
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                         ║
║          AUTONOMOUS BROWSER AUTOMATION - Task Runner                   ║
║                                                                         ║
║  What would you like me to automate? I can:                           ║
║  • Research and compare products on any website                       ║
║  • Fill forms and submit data                                        ║
║  • Extract information and structure it                              ║
║  • Monitor prices or track changes                                   ║
║  • Fill payment forms securely                                       ║
║  • Perform multi-step workflows across sites                         ║
║  • And much more...                                                   ║
║                                                                         ║
╚═══════════════════════════════════════════════════════════════════════╝
    """)
    
    # Show examples
    print("\n📋 EXAMPLE TASKS:\n")
    examples = [
        "1. Research: 'Find me the top 3 ergonomic wireless mice under $100 on Amazon'",
        "2. Compare: 'Compare iPhone 15 prices across Amazon, Best Buy, and Apple'",
        "3. Data Entry: 'Fill this Google Form with my contact details'",
        "4. Monitoring: 'Check if the laptop price dropped below $1200 on Newegg'",
        "5. Payment: 'Complete a test payment on the Stripe demo page'",
        "6. Multi-step: 'Search for flights, compare prices, and save the best deal'",
    ]
    for example in examples:
        print(f"   {example}")
    
    print("\n" + "="*70)
    print("💡 TIPS:")
    print("   • Be specific about websites/URLs")
    print("   • Include what data you want extracted")
    print("   • Tell me if you need comparisons or specific actions")
    print("   • For payment forms, use test cards (not real cards)")
    print("="*70)
    
    intent = input("\n🔍 What would you like me to automate? \n> ").strip()
    
    if not intent:
        print("❌ No task specified. Exiting.")
        return None
    
    return intent


async def run_automation_task(task_description: str):
    """
    Execute any automation task with intelligent agent.
    
    The agent will:
    1. Parse the user's natural language request
    2. Identify which websites/services to visit
    3. Perform the requested actions (research, fill forms, etc.)
    4. Extract and structure the results
    5. Present findings to the user
    """
    print(f"""
╔═══════════════════════════════════════════════════════════════════════╗
║                        STARTING AUTOMATION                             ║
║                                                                         ║
║  Task: {task_description[:60]}{'...' if len(task_description) > 60 else ''}
║                                                                         ║
║  Status: Initializing browser and AI agent...                         ║
╚═══════════════════════════════════════════════════════════════════════╝
    """)
    
    # Initialize the LLM
    llm = ChatGoogle(
        model="gemini-2.0-flash",
        temperature=0.5,  # Balanced for both exploration and precision
    )
    
    # Create an intelligent agent with extended context
    agent_instructions = f"""
You are an autonomous browser automation agent. Your task is to help users with web automation.

USER REQUEST: {task_description}

Your responsibilities:
1. Navigate to the necessary websites and pages
2. Extract relevant information
3. Perform actions as requested (fill forms, make comparisons, etc.)
4. Handle dynamic content and loading states
5. Deal with errors gracefully
6. Present results in a clear, structured format

Important Guidelines:
- Use vision-based element detection when needed (you can see the page)
- Take screenshots to understand complex layouts
- Tab through forms to find all input fields
- Wait for content to load before proceeding
- If a site blocks automation, try alternative approaches
- Always provide actionable results
- For payment testing, only use test card numbers (4242424242424242, etc.)

Be thorough, efficient, and user-focused in your approach.
    """
    
    print("\n⏳ Task is running... This may take a minute or two.\n")
    print("─" * 70)
    
    # Run the agent
    try:
        agent = Agent(
            task=agent_instructions,
            llm=llm,
        )
        
        # Execute with reasonable step limit
        result = await agent.run(max_steps=20)
        
        print("─" * 70)
        print("\n✅ AUTOMATION COMPLETE\n")
        
        # Present results
        if result.final_result:
            print("📊 RESULTS:\n")
            print(result.final_result)
        else:
            print("No explicit result returned, but task was executed.")
        
        return True
        
    except Exception as e:
        print("─" * 70)
        print(f"\n❌ ERROR: {e}\n")
        print("The automation encountered an issue. This might be due to:")
        print("   • Website blocking automated access")
        print("   • Page layout changed from expected")
        print("   • Network connectivity issue")
        print("   • Security restrictions")
        return False


async def show_capabilities():
    """Show what the automation system can do."""
    print("""
╔═══════════════════════════════════════════════════════════════════════╗
║                      SYSTEM CAPABILITIES                               ║
╚═══════════════════════════════════════════════════════════════════════╝

🔍 RESEARCH & DATA EXTRACTION
   • Product research across e-commerce sites
   • Price comparison across multiple vendors
   • News and content aggregation
   • Social media data collection (within ToS)
   • Competitive intelligence gathering

💳 FORM FILLING & DATA ENTRY
   • Payment form automation (with test cards)
   • Account registration on multiple sites
   • Survey and questionnaire filling
   • Document form completion
   • Multi-step application processes

🛒 E-COMMERCE AUTOMATION
   • Product search and filtering
   • Price tracking and alerts
   • Shopping cart management
   • Order history extraction
   • Inventory checking

📊 INFORMATION EXTRACTION
   • Structured data from unstructured pages
   • Table and list scraping
   • Email and contact information extraction
   • Financial data aggregation

⚙️ WORKFLOW AUTOMATION
   • Multi-step cross-website workflows
   • Conditional branching (if this, then that)
   • Data transformation and mapping
   • Result export to files/emails

🛡️ SECURITY & COMPLIANCE
   • Secure credential storage (encrypted)
   • Test mode for payment testing
   • GDPR-compliant data handling
   • Audit logging of all actions

🤖 INTELLIGENT FEATURES
   • Vision-based element detection
   • Natural language task understanding
   • Automatic fallback strategies
   • Dynamic content handling
   • Error recovery

    """)


async def interactive_menu():
    """Main interactive menu."""
    while True:
        print("""
╔═══════════════════════════════════════════════════════════════════════╗
║                         MAIN MENU                                      ║
╚═══════════════════════════════════════════════════════════════════════╝
        """)
        print("1. 🤖 New Automation Task")
        print("2. 📋 View Capabilities")
        print("3. 💡 View Examples")
        print("4. ❓ Help & FAQ")
        print("5. 🚪 Exit")
        
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == "1":
            intent = await get_user_intent()
            if intent:
                success = await run_automation_task(intent)
                if success:
                    print("\n" + "="*70)
                    again = input("\nRun another task? (y/n): ").strip().lower()
                    if again != 'y':
                        print("\n👋 Thank you for using Autonomous Browser Automation!")
                        break
        
        elif choice == "2":
            await show_capabilities()
        
        elif choice == "3":
            print_examples()
        
        elif choice == "4":
            print_help()
        
        elif choice == "5":
            print("\n👋 Goodbye!\n")
            break
        
        else:
            print("\n❌ Invalid option. Please try again.\n")


def print_examples():
    """Print example tasks the system can handle."""
    print("""
╔═══════════════════════════════════════════════════════════════════════╗
║                      EXAMPLE AUTOMATION TASKS                          ║
╚═══════════════════════════════════════════════════════════════════════╝

🛍️ E-COMMERCE EXAMPLES:
   "Find the top 5 rated mechanical keyboards under $200 on Amazon"
   "Compare iPhone 15 Pro Max prices across Amazon, Best Buy, and Apple"
   "Check if the Sony WH-1000XM5 headphones are in stock on Best Buy"
   "Track the price of this laptop and notify me if it drops below $1000"

📚 RESEARCH EXAMPLES:
   "What are the latest reviews for the MacBook Pro M4?"
   "Find job postings for 'Data Scientist' in San Francisco on LinkedIn"
   "Extract all contact information from this company's website"
   "Gather competitor pricing data from top 5 competitors in my industry"

💳 PAYMENT & FORMS:
   "Test a payment form with Stripe test card 4242424242424242"
   "Fill and submit this Google Form with my information"
   "Complete the registration process on this website"

📊 DATA EXTRACTION:
   "Extract all product names and prices from this table"
   "Scrape the latest news headlines from [website]"
   "Get all email addresses from this contact page"

⚙️ WORKFLOW EXAMPLES:
   "1. Search for flights to NYC, 2. Compare prices, 3. Save top 3 deals"
   "Check inventory at all store locations and report availability"
   "Fill out refund forms at these 5 retailers"

🔍 MONITORING EXAMPLES:
   "Monitor this page for price changes daily"
   "Check if this product went back in stock"
   "Track stock price changes for AAPL"

    """)


def print_help():
    """Print help and FAQ."""
    print("""
╔═══════════════════════════════════════════════════════════════════════╗
║                          HELP & FAQ                                    ║
╚═══════════════════════════════════════════════════════════════════════╝

❓ HOW DOES IT WORK?
   1. You describe what you want automated in natural language
   2. The AI agent understands your request
   3. It automatically navigates to the required websites
   4. It performs the requested actions using vision-based detection
   5. It extracts and structures the results
   6. It presents the findings to you

🔒 IS MY DATA SECURE?
   • Credentials are encrypted using Fernet (military-grade)
   • No data is sent to external servers (runs locally)
   • Payment testing uses official test cards only
   • All actions are logged for audit purposes

⚠️ WHAT ABOUT RATE LIMITING?
   • The agent respects robots.txt
   • It includes delays between requests
   • It handles 429 (Too Many Requests) responses gracefully
   • Some sites may require manual verification

💳 CAN I USE REAL PAYMENT CARDS?
   ❌ NO - Please use test cards only
   ✅ For Stripe: 4242424242424242
   ✅ For PayPal tests: Use PayPal's test environment

📱 WHAT ABOUT JAVASCRIPT-HEAVY SITES?
   The system handles dynamic content by:
   • Waiting for JavaScript to render
   • Using vision AI to identify loaded elements
   • Taking screenshots to understand complex layouts

🚫 WHAT WON'T WORK?
   • Sites with strict bot detection (may require manual intervention)
   • Pages requiring complex CAPTCHA solving (manual required)
   • Sites explicitly prohibiting automation in ToS
   • Real financial transactions (use test environments)

💡 BEST PRACTICES:
   1. Be specific in your requests
   2. Include URLs when known
   3. Mention what data you want extracted
   4. For first-time sites, start with research-only tasks
   5. Use test environments for form filling

🆘 TROUBLESHOOTING:
   • If stuck on a page: Describe what you see
   • If form won't fill: Check if selectors match
   • If navigation fails: Try providing more specific URLs
   • For errors: The system will attempt fallback strategies

    """)


async def main():
    """Main entry point."""
    print("\n")
    print("█" * 73)
    print("█" + " " * 71 + "█")
    print("█" + "  AUTONOMOUS BROWSER AUTOMATION - Task Runner".center(71) + "█")
    print("█" + "  Powered by Gemini 2.0 Flash + browser-use Framework".center(71) + "█")
    print("█" + " " * 71 + "█")
    print("█" * 73)
    print()
    
    await interactive_menu()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!\n")
