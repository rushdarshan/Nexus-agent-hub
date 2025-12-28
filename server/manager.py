
import asyncio
import base64
import logging
from typing import Optional, List, Callable, Awaitable
from browser_use import Agent, Browser, BrowserProfile
from examples.fractal_swarm.swarm_manager import (
    run_simulated_swarm,
    run_real_swarm,
    flight_agent_sim,
    hotel_agent_sim,
    itinerary_agent_sim,
)


logger = logging.getLogger(__name__)


class AgentManager:
    def __init__(self):
        self.agent: Optional[Agent] = None
        self.browser: Optional[Browser] = None
        self.browser_context = None
        self.listeners: List[Callable[[dict], Awaitable[None]]] = []
        self.background_task: Optional[asyncio.Task] = None

    async def broadcast(self, data: dict):
        """Send data to all connected websocket listeners"""
        for listener in list(self.listeners):
            try:
                await listener(data)
            except Exception as e:
                logger.error(f"Error executing listener: {e}")

    def add_listener(self, listener: Callable[[dict], Awaitable[None]]):
        self.listeners.append(listener)

    def remove_listener(self, listener: Callable[[dict], Awaitable[None]]):
        if listener in self.listeners:
            self.listeners.remove(listener)

    async def _on_step_end(self, agent: Agent):
        """Callback to extract state and broadcast"""
        # Get latest history item
        if not getattr(agent, 'history', None) or not agent.history.history:
            return

        last_step = agent.history.history[-1]

        # safely get screenshot
        screenshot_b64 = None
        if getattr(last_step.state, 'screenshot', None):
            screenshot_b64 = last_step.state.screenshot
        elif getattr(last_step.state, 'screenshot_path', None):
            # Read from file if path exists
            try:
                with open(last_step.state.screenshot_path, 'rb') as f:
                    screenshot_b64 = base64.b64encode(f.read()).decode('utf-8')
            except Exception:
                pass

        # Just grab a fresh screenshot from the browser if possible to be realtime
        if getattr(agent, 'browser_context', None):
            try:
                page = await agent.browser_context.get_current_page()
                screenshot = await page.screenshot()
                screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
            except Exception:
                # ignore screenshot fetch errors
                pass

        # Model thoughts/response
        thoughts = getattr(last_step, 'model_output', None)
        if thoughts and hasattr(thoughts, 'current_state') and hasattr(thoughts.current_state, 'thinking'):
            thoughts = thoughts.current_state.thinking
        else:
            thoughts = ""

        update_data = {
            "type": "update",
            "screenshot": screenshot_b64,
            "thoughts": thoughts,
            "step": len(agent.history.history),
            "status": "running" if not getattr(agent.state, 'paused', False) else "paused",
        }
        await self.broadcast(update_data)

    async def start_task(self, task: str):
        """Initialize and run a new agent task"""
        if self.agent:
            await self.stop()

        # Initialize browser if needed
        # We stick to one browser instance for now for speed
        if not self.browser:
            self.browser = Browser(browser_profile=BrowserProfile(headless=False))  # Visible for "God Mode" (telepresence)

        # Create agent
        self.agent = Agent(
            task=task,
            browser=self.browser,
            use_vision=True,  # Critical for "God Mode"
        )

        # Run in background
        self.background_task = asyncio.create_task(self._run_agent())

        await self.broadcast({"type": "status", "status": "started", "task": task})

    async def start_swarm(self, task: str, mode: str = "simulate", openrouter_key: str | None = None):
        """Start a Fractal Swarm for the given task.

        mode: 'simulate' or 'real'
        """
        # Stop any existing agent or swarm
        await self.stop()

        async def _run_swarm():
            await self.broadcast({"type": "status", "status": "swarm_started", "task": task, "mode": mode})
            try:
                if mode == "real":
                    result = await run_real_swarm(task, openrouter_key)
                    await self.broadcast({"type": "swarm_result", "result": result})
                else:
                    # Simulate stepwise agent progress so dashboard receives incremental updates
                    agents = [flight_agent_sim(task), hotel_agent_sim(task), itinerary_agent_sim(task)]
                    pending = [asyncio.create_task(a) for a in agents]
                    results = {}
                    for fut in asyncio.as_completed(pending):
                        try:
                            r = await fut
                            results[r["agent"]] = r["result"]
                            # Broadcast incremental update
                            await self.broadcast({"type": "swarm_step", "agent": r["agent"], "result": r["result"]})
                        except Exception as e:
                            logger.error(f"Swarm sub-agent error: {e}")
                            await self.broadcast({"type": "error", "error": str(e)})

                    summary = {"task": task, "results": results}
                    await self.broadcast({"type": "swarm_result", "result": summary})
            except Exception as e:
                logger.error(f"Swarm failed: {e}")
                await self.broadcast({"type": "error", "error": str(e)})

        self.background_task = asyncio.create_task(_run_swarm())

    async def _run_agent(self):
        try:
            # Using the hook
            await self.agent.run(on_step_end=self._on_step_end)

            await self.broadcast({"type": "status", "status": "completed"})

        except Exception as e:
            logger.error(f"Agent failed: {e}")
            await self.broadcast({"type": "error", "error": str(e)})
        finally:
            self.background_task = None

    async def stop(self):
        if self.agent:
            try:
                self.agent.stop()  # Sets state.stopped = True
            except Exception:
                pass
            if self.background_task:
                try:
                    await self.background_task
                except asyncio.CancelledError:
                    pass
            self.agent = None
            await self.broadcast({"type": "status", "status": "stopped"})

    async def pause(self):
        if self.agent:
            try:
                self.agent.pause()
            except Exception:
                pass
            await self.broadcast({"type": "status", "status": "paused"})

    async def resume(self):
        if self.agent:
            try:
                self.agent.resume()
            except Exception:
                pass
            await self.broadcast({"type": "status", "status": "running"})


# Global instance
manager = AgentManager()
