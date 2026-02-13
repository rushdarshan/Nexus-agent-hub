
import asyncio
from intelligent_router import NexusRouter, PlatformDecision

# Mock LLM
class MockLLM:
    async def invoke(self, messages):
        content = messages[1]['content'].lower()
        if "legal" in content or "security" in content:
            return type('obj', (object,), {
                'content': '```json\n{"platform": "delegate", "reasoning": "Specialized task", "steps": ["Audit"], "delegate_to": "SecurityAgent"}\n```'
            })
        else:
             return type('obj', (object,), {
                'content': '```json\n{"platform": "browser", "reasoning": "General research", "steps": ["Search"]}\n```'
            })

async def main():
    print("🚀 STARTING NEXUS GEN 3 DEMO 🚀")
    print("==================================")
    
    router = NexusRouter(llm=MockLLM())
    
    scenarios = [
        "Find the cheapest flight to Tokyo (Standard)",
        "Perform a Security Audit on this repo (A2A Delegation)"
    ]
    
    for i, goal in enumerate(scenarios, 1):
        print(f"\n[Scenario {i}] User Goal: \"{goal}\"")
        # We catch exceptions because real execution might fail without API keys/Browsers
        # but we want to see the routing logic and A2A logs.
        try:
             await router.execute(goal)
        except Exception as e:
            print(f"⚠️ Execution stopped (Expected in demo without full env): {e}")
        print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main())
