"""
Android Agent - AI-powered automation agent for Android devices
Mirrors browser-use's Agent architecture with vision and safety features
"""

import asyncio
import json
import base64
from typing import List, Dict, Any, Optional, Callable, Union
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import logging
import time

from ..device.device import Device, DeviceConfig
from ..hierarchy.hierarchy import ViewHierarchy
from ..controller.controller import AndroidController, controller as default_controller
from ..llm.llm import LLM, LLMConfig, LLMProvider
from .prompts import PromptBuilder, SYSTEM_PROMPT

logger = logging.getLogger('android_use.agent')


class AgentStatus(Enum):
    """Agent execution status"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class AgentConfig:
    """Configuration for Android Agent"""
    max_steps: int = 20
    max_errors: int = 3
    step_delay: float = 1.0
    screenshot_before_action: bool = True
    save_screenshots: bool = True
    output_dir: Path = field(default_factory=lambda: Path("android_output"))
    
    # Safety settings
    budget_limit: float = 2.0  # Max cost in USD
    loop_detection_threshold: int = 3  # Stop after N identical actions
    require_confirmation: bool = False  # Require human confirmation for actions
    
    # LLM settings
    model: str = "openai/gpt-4o-mini"
    temperature: float = 0.3


@dataclass
class AgentStep:
    """Record of a single agent step"""
    step_num: int
    timestamp: str
    action: str
    params: Dict[str, Any]
    reasoning: str
    screenshot_path: Optional[str]
    success: bool
    error: Optional[str] = None
    duration: float = 0.0


@dataclass
class AgentResult:
    """Result of agent execution"""
    task: str
    status: AgentStatus
    steps: List[AgentStep]
    total_steps: int
    total_time: float
    success: bool
    final_message: str
    screenshots: List[str]


class AndroidAgent:
    """
    AI-powered agent that uses Vision and View Hierarchy to control an Android device.
    Implements safety features like budget limits and loop detection.
    """
    
    def __init__(
        self,
        task: str,
        device: Optional[Device] = None,
        llm: Optional[LLM] = None,
        controller: Optional[AndroidController] = None,
        config: Optional[AgentConfig] = None,
        on_step: Optional[Callable[[AgentStep], None]] = None,
    ):
        """
        Initialize Android Agent.
        
        Args:
            task: The task/goal to accomplish
            device: Device instance (auto-created if not provided)
            llm: LLM instance for AI reasoning
            controller: Action controller
            config: Agent configuration
            on_step: Callback function called after each step
        """
        self.task = task
        self.config = config or AgentConfig()
        self.device = device or Device()
        self.controller = controller or default_controller
        self.on_step = on_step
        
        # Initialize LLM
        if llm:
            self.llm = llm
        else:
            self.llm = LLM(LLMConfig(
                provider=LLMProvider.OPENROUTER,
                model=self.config.model,
                temperature=self.config.temperature
            ))
        
        # State
        self.status = AgentStatus.IDLE
        self.history: List[AgentStep] = []
        self.screenshots: List[str] = []
        self.error_count = 0
        self.total_cost = 0.0
        self._recent_actions: List[str] = []  # For loop detection
        
        # Prompt builder
        self.prompt_builder = PromptBuilder(SYSTEM_PROMPT)
        
        # Ensure output directory exists
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Agent initialized for task: {task}")
    
    # ========== Safety Checks ==========
    
    def _check_budget(self) -> bool:
        """Check if within budget limit"""
        # Estimate cost (rough approximation)
        estimated_cost = len(self.history) * 0.01  # ~$0.01 per step
        if estimated_cost > self.config.budget_limit:
            logger.warning(f"Budget limit reached: ${estimated_cost:.2f} > ${self.config.budget_limit}")
            return False
        return True
    
    def _check_loop(self, action: str, params: Dict[str, Any]) -> bool:
        """Detect if agent is stuck in a loop"""
        action_key = f"{action}:{json.dumps(params, sort_keys=True)}"
        self._recent_actions.append(action_key)
        
        # Keep only recent actions
        if len(self._recent_actions) > 10:
            self._recent_actions.pop(0)
        
        # Check for repeated identical actions
        if len(self._recent_actions) >= self.config.loop_detection_threshold:
            recent = self._recent_actions[-self.config.loop_detection_threshold:]
            if len(set(recent)) == 1:
                logger.warning(f"Loop detected: {action} repeated {self.config.loop_detection_threshold} times")
                return True
        
        return False
    
    # ========== Core Methods ==========
    
    async def step(self, step_num: int) -> AgentStep:
        """Execute a single reasoning/action step"""
        start_time = time.time()
        logger.info(f"━━━ Step {step_num}/{self.config.max_steps} ━━━")
        
        # 1. Capture current state
        screenshot = self.device.get_screenshot()
        hierarchy_xml = self.device.get_hierarchy()
        hierarchy = ViewHierarchy(hierarchy_xml)
        current_app = self.device.get_current_app()
        
        # Save screenshot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = None
        if self.config.save_screenshots:
            screenshot_path = self.config.output_dir / f"step_{step_num}_{timestamp}.png"
            screenshot.save(screenshot_path)
            self.screenshots.append(str(screenshot_path))
        
        # 2. Build prompt
        prompt = self.prompt_builder.build_step_prompt(
            task=self.task,
            step=step_num,
            max_steps=self.config.max_steps,
            screen_width=self.device.info.screen_width,
            screen_height=self.device.info.screen_height,
            current_app=f"{current_app.get('package', 'unknown')}",
            elements=hierarchy.to_indexed_prompt(),
            history=[{
                'action': s.action,
                'params': s.params,
                'result': 'success' if s.success else s.error
            } for s in self.history[-5:]]
        )
        
        # 3. Get AI response
        try:
            response = await self.llm.chat(
                prompt=prompt,
                image=screenshot,
                system_prompt=SYSTEM_PROMPT,
                json_response=True
            )
            
            if 'error' in response:
                raise Exception(response['error'])
            
            logger.debug(f"AI Response: {json.dumps(response, indent=2)}")
            
        except Exception as e:
            logger.error(f"LLM error: {e}")
            self.error_count += 1
            return AgentStep(
                step_num=step_num,
                timestamp=timestamp,
                action="error",
                params={},
                reasoning=f"LLM failed: {e}",
                screenshot_path=str(screenshot_path) if screenshot_path else None,
                success=False,
                error=str(e),
                duration=time.time() - start_time
            )
        
        # 4. Check for completion
        if response.get('done', False):
            result_msg = response.get('result', response.get('thought', 'Task completed'))
            logger.info(f"✅ Task completed: {result_msg}")
            return AgentStep(
                step_num=step_num,
                timestamp=timestamp,
                action="done",
                params={},
                reasoning=result_msg,
                screenshot_path=str(screenshot_path) if screenshot_path else None,
                success=True,
                duration=time.time() - start_time
            )
        
        # 5. Extract action - handle different response formats
        action_data = response.get('action', response.get('command', {}))
        
        # Handle case where action is a string (action name directly)
        if isinstance(action_data, str):
            action_name = action_data
            # Try to get params from top level
            params = {}
            for key in ['x', 'y', 'x1', 'y1', 'x2', 'y2', 'text', 'key', 'package', 'url', 'seconds', 'element_id']:
                if key in response:
                    params[key] = response[key]
            
            # Handle element_id -> convert to coordinates
            if 'element_id' in params or 'element_id' in response:
                elem_id = params.pop('element_id', None) or response.get('element_id')
                try:
                    elem_id = int(elem_id)
                    # Get element from current hierarchy
                    from ..hierarchy.hierarchy import ViewHierarchy as VH
                    hierarchy_xml = self.device.get_hierarchy()
                    vh = VH(hierarchy_xml)
                    elem = vh.get_element(elem_id)
                    if elem:
                        params['x'] = elem.center[0]
                        params['y'] = elem.center[1]
                        logger.info(f"Resolved element {elem_id} to ({params['x']}, {params['y']})")
                except Exception as e:
                    logger.warning(f"Could not resolve element_id {elem_id}: {e}")
            
            # Map common action names
            action_map = {'click': 'tap', 'press': 'tap', 'type': 'type_text', 'input': 'type_text'}
            action_name = action_map.get(action_name, action_name)
        else:
            action_name = action_data.get('name', '')
            params = action_data.get('params', {})
        
        reasoning = response.get('thought', response.get('reasoning', ''))
        
        if not action_name:
            logger.warning("No action specified in response")
            return AgentStep(
                step_num=step_num,
                timestamp=timestamp,
                action="none",
                params={},
                reasoning=reasoning or "No action determined",
                screenshot_path=str(screenshot_path) if screenshot_path else None,
                success=False,
                error="No action specified",
                duration=time.time() - start_time
            )
        
        # 6. Safety checks
        if self._check_loop(action_name, params):
            logger.warning("⚠️ Breaking loop - trying alternative action")
            # Try pressing back to break the loop
            action_name = "press_back"
            params = {}
            reasoning = "Breaking detected loop by pressing back"
            self._recent_actions.clear()
        
        if not self._check_budget():
            return AgentStep(
                step_num=step_num,
                timestamp=timestamp,
                action="budget_exceeded",
                params={},
                reasoning="Budget limit reached",
                screenshot_path=str(screenshot_path) if screenshot_path else None,
                success=False,
                error="Budget exceeded",
                duration=time.time() - start_time
            )
        
        # 7. Execute action
        logger.info(f"🎯 Action: {action_name} | Params: {params}")
        logger.info(f"💭 Reasoning: {reasoning}")
        
        try:
            result = await self.controller.execute_action(self.device, action_name, params)
            success = result.get('success', False)
            error = result.get('error') if not success else None
            
            if not success:
                self.error_count += 1
                logger.error(f"Action failed: {error}")
            
        except Exception as e:
            success = False
            error = str(e)
            self.error_count += 1
            logger.error(f"Action execution error: {e}")
        
        # 8. Create step record
        step_record = AgentStep(
            step_num=step_num,
            timestamp=timestamp,
            action=action_name,
            params=params,
            reasoning=reasoning,
            screenshot_path=str(screenshot_path) if screenshot_path else None,
            success=success,
            error=error,
            duration=time.time() - start_time
        )
        
        return step_record
    
    async def run(self) -> AgentResult:
        """
        Run the agent until task completion or max steps.
        
        Returns:
            AgentResult with execution details
        """
        logger.info(f"🚀 Starting task: {self.task}")
        start_time = time.time()
        self.status = AgentStatus.RUNNING
        self.history = []
        self.screenshots = []
        self.error_count = 0
        self._recent_actions = []
        
        final_message = ""
        
        try:
            for i in range(1, self.config.max_steps + 1):
                # Check if should stop
                if self.status == AgentStatus.STOPPED:
                    final_message = "Agent stopped by user"
                    break
                
                if self.error_count >= self.config.max_errors:
                    self.status = AgentStatus.FAILED
                    final_message = f"Too many errors ({self.error_count})"
                    break
                
                # Execute step
                step_result = await self.step(i)
                self.history.append(step_result)
                
                # Callback
                if self.on_step:
                    self.on_step(step_result)
                
                # Check completion
                if step_result.action == "done":
                    self.status = AgentStatus.COMPLETED
                    final_message = step_result.reasoning
                    break
                
                if step_result.action == "budget_exceeded":
                    self.status = AgentStatus.FAILED
                    final_message = "Budget exceeded"
                    break
                
                # Delay between steps
                await asyncio.sleep(self.config.step_delay)
            
            else:
                # Max steps reached
                self.status = AgentStatus.FAILED
                final_message = f"Max steps ({self.config.max_steps}) reached"
        
        except Exception as e:
            self.status = AgentStatus.FAILED
            final_message = f"Agent error: {e}"
            logger.exception("Agent execution failed")
        
        total_time = time.time() - start_time
        
        result = AgentResult(
            task=self.task,
            status=self.status,
            steps=self.history,
            total_steps=len(self.history),
            total_time=total_time,
            success=self.status == AgentStatus.COMPLETED,
            final_message=final_message,
            screenshots=self.screenshots
        )
        
        logger.info(f"━━━ Agent finished ━━━")
        logger.info(f"Status: {self.status.value}")
        logger.info(f"Steps: {len(self.history)}")
        logger.info(f"Time: {total_time:.1f}s")
        logger.info(f"Result: {final_message}")
        
        return result
    
    def stop(self):
        """Stop the agent gracefully"""
        self.status = AgentStatus.STOPPED
        logger.info("Agent stop requested")
    
    def pause(self):
        """Pause the agent"""
        self.status = AgentStatus.PAUSED
        logger.info("Agent paused")
    
    def resume(self):
        """Resume the agent"""
        if self.status == AgentStatus.PAUSED:
            self.status = AgentStatus.RUNNING
            logger.info("Agent resumed")


# Convenience function for quick tasks
async def run_android_task(
    task: str,
    device_serial: str = None,
    model: str = "openai/gpt-4o-mini",
    max_steps: int = 20
) -> AgentResult:
    """
    Quick function to run an Android automation task.
    
    Example:
        result = await run_android_task("Open Settings and enable WiFi")
    """
    device = Device(serial=device_serial)
    config = AgentConfig(max_steps=max_steps, model=model)
    agent = AndroidAgent(task=task, device=device, config=config)
    return await agent.run()
