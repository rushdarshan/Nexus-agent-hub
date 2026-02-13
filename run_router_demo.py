
import asyncio
from intelligent_router import NexusRouter, PlatformDecision

# Mock LLM to avoid API key dependency for this demo
class MockLLM:
    async def invoke(self, messages):
        # basic keyword matching to simulate "intelligence" for the demo
        content = messages[1]['content'].lower()
        if "instagram" in content or "tiktok" in content or "app" in content:
            return type('obj', (object,), {
                'content': '```json\n{"platform": "android", "reasoning": "User mentioned mobile apps (Instagram/TikTok) which are better handled by the Android agent.", "steps": ["Open App", "Do action"]}\n```'
            })
        elif "handoff" in content or "hybrid" in content or ("web" in content and "app" in content):
            return type('obj', (object,), {
                'content': '```json\n{"platform": "hybrid", "reasoning": "Complex task requiring both Web search and App execution.", "steps": ["Search Web", "Open App"]}\n```'
            })
        else:
            return type('obj', (object,), {
                'content': '```json\n{"platform": "browser", "reasoning": "Standard web research task.", "steps": ["Navigate to website", "Extract info"]}\n```'
            })

async def main():
    print("🚀 STARTING NEXUS ROUTER DEMO 🚀")
    print("==================================")
    
    router = NexusRouter(llm=MockLLM())
    
    scenarios = [
        "Find the cheapest flight to Tokyo on Google Flights",
        "Like the last 5 posts on my Instagram feed",
        "Search for 'Best Pasta' on Google, then open UberEats app to order it (Hybrid)"
    ]
    
    for i, goal in enumerate(scenarios, 1):
        print(f"\n[Scenario {i}] User Goal: \"{goal}\"")
        decision = await router.route_task(goal)
        print(f"🤖 AI DECISION: {decision.platform.upper()}")
        print(f"📝 REASONING: {decision.reasoning}")
        print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main())
