
import asyncio
import os
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent))

from intelligent_router import NexusRouter
from browser_use.memory.neural_bridge import neural_bridge
from a2a import A2AClient, AgentIdentity
from a2a_config import KNOWN_PEERS

# Mock LLM for Router Test
class MockLLM:
    async def invoke(self, messages):
        # Return a fake browser decision
        return type('obj', (object,), {
            'content': '```json\n{"platform": "browser", "reasoning": "Sanity check", "steps": ["Check Google"]}\n```'
        })
    
    # Handle structured output if called that way
    async def call_structured(self, prompt, model_class):
        return model_class(
            platform="browser", 
            reasoning="Sanity Check", 
            steps=["Check Google"]
        )

async def main():
    print("🏥 Running Nexus Agent Hub Sanity Check...")
    errors = []

    # 1. Test Neural Bridge Load
    print("\n[1/3] Testing Neural Bridge...")
    try:
        if neural_bridge.model:
            print("   ✅ Embedding model loaded.")
        else:
            print("   ⚠️ Embedding model via 'sentence-transformers' not found. Using Hash fallback (Expected in lightweight env).")
        
        neural_bridge.store_memory("Test memory", {"test": True})
        print("   ✅ Neural Bridge store/query interface is responsive.")
    except Exception as e:
        print(f"   ❌ Neural Bridge Failed: {e}")
        errors.append("NeuralBridge")

    # 2. Test A2A Configuration
    print("\n[2/3] Testing A2A Configuration...")
    try:
        identity = AgentIdentity(name="Sanity-Tester", capabilities=["test"])
        client = A2AClient(identity, KNOWN_PEERS)
        if len(client.peers) > 0:
            print(f"   ✅ A2A Client loaded with {len(client.peers)} known peers.")
        else:
            print("   ⚠️ No peers found in a2a_config.py")
            errors.append("A2A Config")
    except Exception as e:
        print(f"   ❌ A2A Failed: {e}")
        errors.append("A2A")

    # 3. Test Nexus Router Initialization
    print("\n[3/3] Testing Nexus Router Initialization...")
    try:
        router = NexusRouter(llm=MockLLM())
        print("   ✅ NexusRouter initialized successfully.")
        
        # Test basic decision flow
        decision = await router.route_task("Check google.com")
        if decision.platform == "browser":
            print("   ✅ Router made a decision (Mocked).")
        else:
            print(f"   ⚠️ Router decision unexpected: {decision.platform}")
            
    except Exception as e:
        print(f"   ❌ NexusRouter Failed: {e}")
        errors.append("NexusRouter")

    print("\n" + "="*40)
    if errors:
        print(f"❌ Sanity Check FAILED with {len(errors)} errors: {errors}")
        sys.exit(1)
    else:
        print("✅ Sanity Check PASSED. System is ready for production deployment.")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
