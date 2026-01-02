"""
Simple example demonstrating android-use

Run: python -m android_use.examples.simple
"""

import asyncio
import os
import sys

# Add parent to path for development
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from android_use import AndroidAgent, Device, AgentConfig


async def main():
    """Simple example: Open Settings and navigate"""
    
    print("🤖 Android-Use Simple Example")
    print("=" * 40)
    
    # 1. Connect to device
    print("\n📱 Connecting to device...")
    device = Device()
    print(f"✓ Connected to {device.info.brand} {device.info.model}")
    print(f"  Screen: {device.info.screen_width}x{device.info.screen_height}")
    
    # 2. Configure agent with safety limits
    config = AgentConfig(
        max_steps=15,
        budget_limit=1.0,
        step_delay=1.5,
        save_screenshots=True,
        model="openai/gpt-4o-mini"
    )
    
    # 3. Define task
    task = "Open the Settings app and find the Display settings"
    print(f"\n📋 Task: {task}")
    
    # 4. Track progress
    def on_step(step):
        status = "✓" if step.success else "✗"
        print(f"  {status} Step {step.step_num}: {step.action}")
        if step.reasoning:
            print(f"    └─ {step.reasoning[:60]}...")
    
    # 5. Create and run agent
    agent = AndroidAgent(
        task=task,
        device=device,
        config=config,
        on_step=on_step
    )
    
    print("\n🚀 Starting agent...")
    result = await agent.run()
    
    # 6. Print results
    print("\n" + "=" * 40)
    print("📊 Results:")
    print(f"  Status: {result.status.value}")
    print(f"  Success: {result.success}")
    print(f"  Steps: {result.total_steps}")
    print(f"  Time: {result.total_time:.1f}s")
    print(f"  Message: {result.final_message}")
    
    if result.screenshots:
        print(f"\n📸 Screenshots saved to: android_output/")
    
    return result


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run
    asyncio.run(main())
