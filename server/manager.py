import asyncio
import base64
import logging
import sys
import os
import atexit
from pathlib import Path
from typing import Optional, List, Callable, Awaitable

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from browser_use import Agent, Browser, BrowserProfile
from swarm_coordinator import SwarmCoordinator
from swarm_brain import get_brain


logger = logging.getLogger(__name__)


class AgentManager:
    def __init__(self):
        self.agent: Optional[Agent] = None
        self.browser: Optional[Browser] = None
        self.browser_context = None
        self.listeners: List[Callable[[dict], Awaitable[None]]] = []
        self.background_task: Optional[asyncio.Task] = None
        self.background_process = None
        
        # Ensure subprocess is killed on exit
        atexit.register(self._cleanup_process)

    def _cleanup_process(self):
        """Kill background process on shutdown"""
        if self.background_process and self.background_process.poll() is None:
            logger.info(f"🛑 Killing zombie process {self.background_process.pid}")
            self.background_process.terminate()
            try:
                self.background_process.wait(timeout=2)
            except:
                self.background_process.kill()

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
        """Initialize and run a new agent task via subprocess with output streaming"""
        if self.agent:
            await self.stop()

        try:
            import subprocess
            import threading
            
            # Get path to cli_agent.py
            cli_agent_path = Path(__file__).parent.parent / "cli_agent.py"
            
            # Prepare environment with enforced UTF-8 encoding
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"

            # Spawn the agent as a separate process with piped output
            self.background_process = subprocess.Popen(
                [sys.executable, "-u", str(cli_agent_path), task],  # -u for unbuffered output
                cwd=str(Path(__file__).parent.parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                text=True,
                encoding='utf-8',
                bufsize=1,  # Line buffered
            )
            
            logger.info(f"🚀 Spawned agent process PID: {self.background_process.pid}")
            await self.broadcast({"type": "status", "status": "started", "task": task})
            
            # Capture the current loop
            loop = asyncio.get_running_loop()
            
            # Start a background thread to read and broadcast output
            def stream_output():
                try:
                    for line in iter(self.background_process.stdout.readline, ''):
                        if line:
                            # Use asyncio to broadcast from thread to main loop
                            asyncio.run_coroutine_threadsafe(
                                self.broadcast({
                                    "type": "terminal_output",
                                    "line": line.rstrip()
                                }),
                                loop
                            )
                    
                    # Process finished
                    exit_code = self.background_process.wait()
                    asyncio.run_coroutine_threadsafe(
                        self.broadcast({
                            "type": "status",
                            "status": "completed" if exit_code == 0 else "failed"
                        }),
                        loop
                    )
                except Exception as e:
                    logger.error(f"Stream error: {e}")
            
            # Start streaming thread
            self.stream_thread = threading.Thread(target=stream_output, daemon=True)
            self.stream_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to start agent: {e}")
            await self.broadcast({"type": "error", "error": str(e)})
            raise


    async def start_swarm(self, task: str, mode: str = "real", openrouter_key: str | None = None):
        """Start a Fractal Swarm for the given task using SwarmCoordinator."""
        # Stop any existing agent or swarm
        await self.stop()

        async def _run_swarm():
            await self.broadcast({"type": "status", "status": "swarm_started", "task": task, "mode": mode})
            try:
                # Use our SwarmCoordinator
                coordinator = SwarmCoordinator(goal=task, headless=False)
                
                # Custom broadcast wrapper to send updates to dashboard
                original_store = coordinator.brain.store_finding
                
                async def store_and_broadcast(session_id, finding):
                    original_store(session_id, finding)
                    await self.broadcast({
                        "type": "swarm_step",
                        "agent": finding.agent_name,
                        "result": finding.finding[:500]  # Truncate for display
                    })
                
                coordinator.brain.store_finding = store_and_broadcast
                
                # Run the full swarm workflow
                decision = await coordinator.run()
                
                # Broadcast final result
                result = {
                    "task": task,
                    "recommendation": decision.recommendation,
                    "sources": decision.sources
                }
                await self.broadcast({"type": "swarm_result", "result": result})
                
            except Exception as e:
                logger.error(f"Swarm failed: {e}")
                await self.broadcast({"type": "error", "error": str(e)})

        self.background_task = asyncio.create_task(_run_swarm())

    async def _run_agent(self):
        try:
            logger.info("🚀 Starting agent execution...")
            
            # Run the agent (max_steps limits the execution)
            result = await self.agent.run(max_steps=15)
            
            logger.info(f"✅ Agent completed: {result}")
            await self.broadcast({"type": "status", "status": "completed"})

        except Exception as e:
            logger.error(f"❌ Agent failed: {e}", exc_info=True)
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
