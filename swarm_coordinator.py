#!/usr/bin/env python3
"""
SWARM COORDINATOR - Orchestrate Multiple Agents with a CEO
===========================================================
This is the "Fractal Swarm" architecture:
1. CEO Agent receives the goal
2. CEO delegates to Worker Agents
3. Workers report findings to the Brain
4. CEO synthesizes and gives final answer
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from browser_use import Agent, BrowserProfile, BrowserSession
from browser_use.llm import ChatGoogle
from swarm_brain import SwarmBrain, Finding, Decision, get_brain


@dataclass
class WorkerTask:
    """A task assigned to a worker agent."""
    name: str
    objective: str
    search_site: str  # e.g., "kayak.com", "google.com/flights"
    

class SwarmCoordinator:
    """
    The mastermind that coordinates the swarm.
    
    Flow:
    1. User gives goal → CEO plans tasks
    2. Workers execute in parallel → Report to Brain
    3. CEO reads Brain → Synthesizes final answer
    """
    
    def __init__(self, goal: str, headless: bool = False):
        self.goal = goal
        self.headless = headless
        self.brain = get_brain()
        self.session_id = self.brain.create_session(goal)
        self.llm = ChatGoogle(model="gemini-2.0-flash", temperature=0.3)
        
        print(f"🧠 SwarmCoordinator initialized")
        print(f"   Session: {self.session_id}")
        print(f"   Goal: {goal}")
    
    async def plan_tasks(self) -> List[WorkerTask]:
        """Have the CEO agent plan what tasks to delegate."""
        
        planning_prompt = f"""
You are a CEO agent coordinating a team of browser automation agents.

GOAL: {self.goal}

Your job is to break this goal into 3-4 specific research tasks that can be done IN PARALLEL by different agents.
Each agent will visit ONE website and extract specific information.

Respond in this exact format (one task per line):
TASK: [Agent Name] | [Website to visit] | [Specific objective]

Example for "Find best flight NYC to Tokyo":
TASK: Kayak Agent | kayak.com | Search for NYC to Tokyo flights, note cheapest option with price and duration
TASK: Google Flights Agent | google.com/flights | Search NYC to Tokyo, find best value flight
TASK: Skyscanner Agent | skyscanner.com | Compare NYC Tokyo flights, note any deals
TASK: Expedia Agent | expedia.com | Check NYC Tokyo flight prices and bundles

Now plan tasks for: {self.goal}
"""
        
        # Use a simple LLM call (not browser agent) for planning
        from langchain_google_genai import ChatGoogleGenerativeAI
        planner = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.3)
        response = planner.invoke(planning_prompt)
        
        tasks = []
        for line in response.content.split('\n'):
            if line.strip().startswith('TASK:'):
                parts = line.replace('TASK:', '').strip().split('|')
                if len(parts) >= 3:
                    tasks.append(WorkerTask(
                        name=parts[0].strip(),
                        search_site=parts[1].strip(),
                        objective=parts[2].strip()
                    ))
        
        print(f"\n📋 CEO planned {len(tasks)} tasks:")
        for t in tasks:
            print(f"   → {t.name}: {t.objective[:50]}...")
        
        return tasks
    
    async def run_worker(self, task: WorkerTask) -> Optional[Finding]:
        """Run a single worker agent and store its finding."""
        
        print(f"\n🤖 [{task.name}] Starting on {task.search_site}...")
        
        browser_session = BrowserSession(
            browser_profile=BrowserProfile(
                headless=self.headless,
                disable_security=True
            )
        )
        
        worker_prompt = f"""
You are {task.name}, a research agent.

YOUR TASK: {task.objective}
WEBSITE: Go to {task.search_site}

IMPORTANT INSTRUCTIONS:
1. Navigate to the website
2. Search/find the information requested
3. Extract SPECIFIC data (prices, times, details)
4. Return a structured finding with exact numbers

Be precise. Return actual data, not vague summaries.
End with: FINDING: [your specific finding with numbers/details]
"""
        
        try:
            agent = Agent(
                task=worker_prompt,
                llm=self.llm,
                browser_session=browser_session
            )
            
            result = await agent.run(max_steps=12)
            
            # Extract the finding
            result_text = str(result.final_result()) if hasattr(result, 'final_result') else str(result)
            
            # Get current URL from browser
            current_url = task.search_site  # Simplified; could extract from browser state
            
            finding = Finding(
                agent_name=task.name,
                task=task.objective,
                finding=result_text,
                source_url=current_url,
                confidence=0.8,  # Could be smarter about this
                timestamp=datetime.now().isoformat()
            )
            
            # Store in brain
            self.brain.store_finding(self.session_id, finding)
            
            print(f"✅ [{task.name}] Completed: {result_text[:100]}...")
            return finding
            
        except Exception as e:
            print(f"❌ [{task.name}] Failed: {e}")
            
            # Store failure as finding
            finding = Finding(
                agent_name=task.name,
                task=task.objective,
                finding=f"FAILED: {str(e)}",
                source_url=task.search_site,
                confidence=0.0,
                timestamp=datetime.now().isoformat()
            )
            self.brain.store_finding(self.session_id, finding)
            return finding
            
        finally:
            try:
                await browser_session.close()
            except:
                pass
    
    async def run_ceo_synthesis(self) -> Decision:
        """Have the CEO agent synthesize all findings into a decision."""
        
        print("\n🎯 CEO Agent synthesizing results...")
        
        # Get context from brain
        context = self.brain.get_context_for_ceo(self.session_id)
        
        synthesis_prompt = f"""
You are the CEO agent. Your worker agents have completed their research.

ORIGINAL GOAL: {self.goal}

{context}

Based on ALL the findings above, provide:
1. RECOMMENDATION: The best option/answer (be specific!)
2. REASONING: Why this is the best choice
3. ALTERNATIVES: Other good options if the first doesn't work

Be decisive. Give a clear, actionable recommendation.
"""
        
        from langchain_google_genai import ChatGoogleGenerativeAI
        ceo = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2)
        response = ceo.invoke(synthesis_prompt)
        
        decision = Decision(
            question=self.goal,
            recommendation=response.content,
            reasoning="Synthesized from multiple agent findings",
            sources=[f.source_url for f in self.brain.get_session_findings(self.session_id)],
            timestamp=datetime.now().isoformat()
        )
        
        # Store decision
        self.brain.store_decision(self.session_id, decision)
        
        return decision
    
    async def run(self) -> Decision:
        """Execute the full swarm workflow."""
        
        print("=" * 60)
        print("🔥 SWARM COORDINATOR - Starting")
        print("=" * 60)
        
        # Phase 1: CEO plans tasks
        tasks = await self.plan_tasks()
        
        if not tasks:
            raise ValueError("CEO failed to plan any tasks")
        
        # Phase 2: Run all workers in parallel
        print("\n" + "=" * 60)
        print("🚀 Launching Worker Agents in Parallel")
        print("=" * 60)
        
        worker_results = await asyncio.gather(
            *[self.run_worker(task) for task in tasks],
            return_exceptions=True
        )
        
        # Phase 3: CEO synthesizes
        print("\n" + "=" * 60)
        print("🧠 CEO Synthesizing Results")
        print("=" * 60)
        
        decision = await self.run_ceo_synthesis()
        
        # Final output
        print("\n" + "=" * 60)
        print("📊 FINAL DECISION")
        print("=" * 60)
        print(f"\n{decision.recommendation}")
        print("\n" + "=" * 60)
        
        return decision


async def main():
    """Example usage."""
    
    # Check API key
    if "GOOGLE_API_KEY" not in os.environ:
        print("❌ GOOGLE_API_KEY not set")
        return
    
    # Example: Flight search
    goal = input("\n🎯 What do you want the swarm to research?\n> ").strip()
    
    if not goal:
        goal = "Find the best flight from New York to Tokyo for next month, considering price and comfort"
    
    coordinator = SwarmCoordinator(goal=goal, headless=False)
    decision = await coordinator.run()
    
    # Export session
    session_data = coordinator.brain.export_session(coordinator.session_id)
    
    output_file = f"swarm_session_{coordinator.session_id}.json"
    import json
    with open(output_file, 'w') as f:
        json.dump(session_data, f, indent=2)
    
    print(f"\n💾 Session saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
