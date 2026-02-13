
import asyncio
from typing import Literal, List, Optional
from pydantic import BaseModel, Field
from browser_use.llm.base import BaseChatModel
from browser_use.agent.service import Agent
from browser_use import Browser

# Import the Android Agent (assuming it's available from the legacy import or similar path)
try:
    from android_agent_simple import AndroidAgent
except ImportError:
    # Fallback or mock if the file was moved/renamed differently
    class AndroidAgent:
        def __init__(self, workspace): pass
        async def run(self, task, max_steps): return "Android Agent Mock Result"



class PlatformDecision(BaseModel):
    platform: Literal["browser", "android", "hybrid", "delegate"] = Field(..., description="The platform to use for the user's goal.")
    reasoning: str = Field(..., description="The reasoning behind the platform choice.")
    steps: List[str] = Field(..., description="List of high-level steps to execute.")
    delegate_to: Optional[str] = Field(None, description="If platform is 'delegate', the type of agent needed (e.g. 'Legal', 'Security').")

class NexusRouter:
    """
    Intelligent Router for DevDash 2026.
    Decides whether to use Browser, Android, Both (Hybrid), or Delegate to an external Specialist Agent.
    """
    def __init__(self, llm: BaseChatModel):
        self.llm = llm
        self.browser = Browser(headless=False) # Keep one browser instance alive
        
        # Initialize A2A
        from a2a import A2AClient, AgentIdentity
        from a2a_config import KNOWN_PEERS
        self.identity = AgentIdentity(name="Nexus-Hub-Core", capabilities=["orchestration", "browsing", "android-control"])
        self.a2a = A2AClient(self.identity, KNOWN_PEERS)

    async def route_task(self, user_goal: str) -> PlatformDecision:
        print(f"🧠 Routing Goal: {user_goal}")
        
        prompt = f"""
        You are the Nexus Supervisor. You have the following execution paths:
        1. WEB AGENT: Research, browsing, finding info.
        2. ANDROID AGENT: Mobile apps (Instagram, TikTok), simple APIs.
        3. DELEGATE: Complex specialized tasks outside your scope (e.g. Legal review, Security Audit, Crypto analysis).
        
        GOAL: {user_goal}
        
        Decide the best execution path.
        - If it requires browsing and apps, use 'hybrid'.
        - If it requires specialized knowledge (Legal, Security), use 'delegate'.
        """
        
        system_prompt = "You are a routing assistant. Respond ONLY with valid JSON matching the PlatformDecision schema."
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        try:
             if hasattr(self.llm, 'call_structured'):
                 decision = await self.llm.call_structured(prompt, PlatformDecision)
             else:
                 result = await self.llm.invoke(messages)
                 content = result.content
                 import json
                 if "```json" in content:
                     content = content.split("```json")[1].split("```")[0]
                 data = json.loads(content)
                 decision = PlatformDecision(**data)
                 
        except Exception as e:
            print(f"⚠️ Routing failed, defaulting to Browser. Error: {e}")
            decision = PlatformDecision(platform="browser", reasoning="Fallback due to error", steps=[user_goal])

        return decision

    async def execute(self, goal: str):
        plan = await self.route_task(goal)
        print(f"👉 Strategy: {plan.platform.upper()} because {plan.reasoning}")
        
        if plan.platform == "browser":
            await self._run_browser(plan.steps)
        elif plan.platform == "android":
            await self._run_android(plan.steps)
        elif plan.platform == "hybrid":
            print("🔄 Initiating Cross-Platform Handoff...")
            web_context = await self._run_browser(plan.steps[:1]) 
            await self._run_android(plan.steps[1:], context=web_context)
        elif plan.platform == "delegate":
            await self._delegate_task(goal, plan.delegate_to)

    async def _delegate_task(self, goal: str, agent_type: str):
        print(f"📡 Initiating A2A Negotiation for: {goal}")
        
        # 1. Broadcast RFP
        bids = await self.a2a.broadcast_rfp(goal)
        
        if not bids:
            print("❌ No agents responded to the RFP. Falling back to Browser.")
            await self._run_browser([goal])
            return

        # 2. Select Winner (Simple lowest cost logic for now)
        print(f"📨 Received {len(bids)} bids:")
        for bid in bids:
            print(f"   - {bid.agent_name}: ${bid.proposed_cost} ({bid.estimated_time}) -> {bid.rationale}")
            
        winner = bids[0] # Just pick the first one for demo
        
        # 3. Delegate
        result = await self.a2a.delegate_task(winner.agent_id, goal)
        print(f"✅ Delegate Task Complete!\n{result}")

    async def _run_browser(self, steps: List[str]) -> str:
        print(f"🌐 Running Browser Steps: {steps}")
        # Combine steps into one task for the agent
        task = " ".join(steps)
        
        # MCP Integration
        from mcp_config import get_enabled_servers
        from browser_use.mcp.client import MCPClient
        from browser_use.tools.service import Tools
        from contextlib import AsyncExitStack
        
        tools = Tools()
        servers = get_enabled_servers()
        
        async with AsyncExitStack() as stack:
            # Connect to all enabled MCP servers
            for server in servers:
                try:
                    client = MCPClient(
                        server_name=server.name,
                        command=server.command,
                        args=server.args,
                        env=server.env
                    )
                    # Enter context (connects to server)
                    await stack.enter_async_context(client)
                    # Register tools
                    await client.register_to_tools(tools)
                    print(f"🔌 Connected to MCP: {server.name}")
                except Exception as e:
                    print(f"❌ Failed to connect to MCP {server.name}: {e}")

            # Run Agent with loaded tools
            agent = Agent(task=task, llm=self.llm, browser=self.browser, tools=tools)
            history = await agent.run()
            
            # Extract meaningful result
            result = history.final_result() if hasattr(history, 'final_result') else str(history)
            return result

    async def _run_android(self, steps: List[str], context: str = ""):
        print(f"📱 Running Android Steps: {steps} with context len={len(context)}")
        task = " ".join(steps)
        if context:
            task = f"Context from previous step: {context}\n\nTask: {task}"
            
        android = AndroidAgent(workspace="./android_workspace")
        await android.run(task)

# Helper to run easily
async def run_nexus(goal: str):
    from browser_use.llm.openai import ChatOpenAI # Example import
    # Initialize your LLM here
    # llm = ChatOpenAI(model="gpt-4o") 
    # For now we'll just print instructions as we don't have the API key in this file
    print("Please initialize NexusRouter with a valid LLM instance in your main script.")
