"""Specialized Agents for Enterprise Workflows.

Each agent is a specialist in its domain:
- DispatcherAgent: Analyzes intent, routes to specialists
- ResearcherAgent: Deep web research, data extraction
- ComplianceAgent: GDPR/CCPA checks, robots.txt, legal
- WorkerAgent: Form filling, data entry, browser automation
"""
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from urllib.parse import urlparse
import re

if TYPE_CHECKING:
    from browser_use import Agent, BrowserSession
    from browser_use.enterprise.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


@dataclass
class AgentCapability:
    """Describes what an agent can do."""
    name: str
    description: str
    keywords: List[str]
    requires_browser: bool = True
    requires_auth: bool = False


class BaseSpecialistAgent(ABC):
    """
    Base class for all specialist agents.
    
    Each specialist agent wraps browser-use's Agent with domain-specific
    prompts, tools, and validation logic.
    """
    
    def __init__(
        self,
        llm: Any = None,
        browser_session: Optional["BrowserSession"] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        self.llm = llm
        self.browser_session = browser_session
        self.name = name or self.__class__.__name__
        self.description = description or ""
        self.orchestrator: Optional["Orchestrator"] = None
        self._browser_agent: Optional["Agent"] = None
        
    @property
    @abstractmethod
    def capabilities(self) -> List[AgentCapability]:
        """Return list of capabilities this agent provides."""
        pass
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the specialized system prompt for this agent."""
        pass
    
    @abstractmethod
    async def execute(self, intent: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task based on intent."""
        pass
    
    async def _get_browser_agent(self) -> "Agent":
        """Lazily create browser-use Agent with specialized config."""
        if self._browser_agent is None:
            from browser_use import Agent
            
            self._browser_agent = Agent(
                task="",  # Set per-task
                llm=self.llm,
                browser=self.browser_session,
                use_vision=True,
            )
        return self._browser_agent


class DispatcherAgent(BaseSpecialistAgent):
    """
    Analyzes user intent and routes to appropriate specialist agents.
    
    The Dispatcher is the "brain" that decomposes complex tasks into
    subtasks and assigns them to the right specialists.
    """
    
    @property
    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                name="intent_analysis",
                description="Analyze natural language to understand user goals",
                keywords=["analyze", "understand", "plan"],
                requires_browser=False,
            ),
            AgentCapability(
                name="task_decomposition",
                description="Break complex tasks into actionable subtasks",
                keywords=["break down", "decompose", "plan"],
                requires_browser=False,
            ),
        ]
    
    @property
    def system_prompt(self) -> str:
        return """You are a Dispatcher Agent for an enterprise automation system.

Your role is to:
1. Analyze the user's intent and break it into concrete subtasks
2. Assign each subtask to the most appropriate specialist agent
3. Identify dependencies between subtasks
4. Flag any compliance or security concerns

Available specialist agents:
- researcher: Web research, data extraction, market analysis
- compliance: Legal checks, GDPR/CCPA, robots.txt validation
- worker: Form filling, data entry, browser automation

Output a structured plan with subtasks, assigned agents, and execution order."""

    async def analyze(self, intent: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze intent and create execution plan."""
        # In production: use LLM to analyze
        # For now: rule-based decomposition
        
        subtasks = []
        intent_lower = intent.lower()
        
        # Always start with compliance check for external sites
        if any(kw in intent_lower for kw in ["website", "site", "scrape", "extract", "portal"]):
            subtasks.append({
                "intent": f"Check compliance for: {intent}",
                "agent": "compliance",
                "priority": 3,  # HIGH
                "context": {"original_intent": intent},
            })
        
        # Research tasks
        if any(kw in intent_lower for kw in ["research", "find", "search", "compare", "analyze market"]):
            subtasks.append({
                "intent": intent,
                "agent": "researcher",
                "priority": 2,
                "context": context,
            })
        
        # Worker tasks (form filling, data entry)
        if any(kw in intent_lower for kw in ["fill", "submit", "enter", "login", "upload", "download"]):
            subtasks.append({
                "intent": intent,
                "agent": "worker",
                "priority": 2,
                "context": context,
            })
        
        # Default: if no specific match, use worker
        if not subtasks:
            subtasks.append({
                "intent": intent,
                "agent": "worker",
                "priority": 2,
                "context": context,
            })
        
        return {
            "original_intent": intent,
            "subtasks": subtasks,
            "execution_order": "sequential" if len(subtasks) > 1 else "single",
        }
    
    async def execute(self, intent: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatcher doesn't execute - it analyzes."""
        return await self.analyze(intent, context)


class ResearcherAgent(BaseSpecialistAgent):
    """
    Performs deep web research and data extraction.
    
    Specializes in:
    - Multi-site research across social platforms
    - Competitor analysis
    - Market trend identification
    - Data extraction and structuring
    """
    
    def __init__(
        self,
        llm: Any = None,
        browser_session: Optional["BrowserSession"] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        specialization: Optional[str] = None,
    ):
        super().__init__(llm, browser_session, name, description)
        self.specialization = specialization or "general"
    
    @property
    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                name="web_research",
                description="Research topics across multiple websites",
                keywords=["research", "find", "search"],
            ),
            AgentCapability(
                name="data_extraction",
                description="Extract structured data from web pages",
                keywords=["extract", "scrape", "get data"],
            ),
            AgentCapability(
                name="competitor_analysis",
                description="Analyze competitor websites and pricing",
                keywords=["competitor", "compare", "pricing"],
            ),
        ]
    
    @property
    def system_prompt(self) -> str:
        return """You are a Research Agent specialized in web intelligence gathering.

Your capabilities:
1. Navigate to websites and extract relevant information
2. Compare data across multiple sources
3. Identify trends and patterns
4. Structure findings in clear, actionable format

Guidelines:
- Always verify information from multiple sources when possible
- Respect rate limits and robots.txt
- Extract only publicly available information
- Provide citations/sources for all findings

Output structured research findings with sources."""

    async def execute(self, intent: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute research task using browser-use."""
        logger.info(f"🔬 Researcher executing: {intent[:50]}...")
        
        agent = await self._get_browser_agent()
        
        # Enhance task with research-specific instructions
        research_task = f"""Research Task: {intent}

Instructions:
1. Navigate to relevant websites
2. Extract key information
3. Take screenshots of important findings
4. Compile a structured summary

Context: {context}

Provide findings in a structured format."""

        try:
            # Update agent task and run
            agent.task = research_task
            result = await agent.run()
            
            return {
                "status": "completed",
                "findings": result.final_result() if hasattr(result, 'final_result') else str(result),
                "sources": [],  # Would be populated from agent's navigation history
                "intent": intent,
            }
        except Exception as e:
            logger.error(f"Research failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "intent": intent,
            }


class ComplianceAgent(BaseSpecialistAgent):
    """
    Ensures all automation actions comply with legal and ethical standards.
    
    Checks:
    - robots.txt compliance
    - GDPR/CCPA data handling
    - Terms of Service violations
    - Rate limiting adherence
    """
    
    BLOCKED_PATTERNS = [
        r"bank.*login",
        r"payment.*credentials",
        r"social\s*security",
        r"passport.*number",
    ]
    
    def __init__(
        self,
        llm: Any = None,
        browser_session: Optional["BrowserSession"] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        rules: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(llm, browser_session, name, description)
        self.rules = rules or {}
    
    @property
    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                name="robots_txt_check",
                description="Verify robots.txt allows automation",
                keywords=["robots", "crawl", "scrape"],
                requires_browser=False,
            ),
            AgentCapability(
                name="gdpr_compliance",
                description="Check GDPR/CCPA compliance for data handling",
                keywords=["gdpr", "ccpa", "privacy", "data"],
                requires_browser=False,
            ),
            AgentCapability(
                name="tos_review",
                description="Review terms of service for automation restrictions",
                keywords=["terms", "service", "legal"],
            ),
        ]
    
    @property
    def system_prompt(self) -> str:
        return """You are a Compliance Agent ensuring legal and ethical automation.

Your responsibilities:
1. Check robots.txt before any scraping
2. Ensure GDPR/CCPA compliance for personal data
3. Identify potential Terms of Service violations
4. Flag sensitive operations requiring human approval

Always err on the side of caution. If uncertain, require human approval."""

    async def check(self, intent: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Quick compliance check for an intent."""
        issues = []
        
        # Check for blocked patterns
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, intent.lower()):
                issues.append(f"Blocked pattern detected: {pattern}")
        
        # Check if URLs in context have robots.txt restrictions
        urls = context.get("urls", [])
        for url in urls:
            robots_ok = await self._check_robots_txt(url, "/")
            if not robots_ok:
                issues.append(f"robots.txt may restrict: {url}")
        
        # Check for PII handling
        if any(kw in intent.lower() for kw in ["email", "phone", "address", "personal"]):
            issues.append("Task involves personal data - ensure GDPR compliance")
        
        return {
            "approved": len(issues) == 0,
            "issues": issues,
            "reason": issues[0] if issues else None,
            "requires_human_review": len(issues) > 0,
        }
    
    async def _check_robots_txt(self, url: str, path: str) -> bool:
        """Check if robots.txt allows access to path."""
        try:
            import httpx
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(robots_url, timeout=5.0)
                if response.status_code == 200:
                    content = response.text.lower()
                    # Simple check - in production use robotsparser
                    if "disallow: /" in content and "user-agent: *" in content:
                        return False
            return True
        except Exception:
            return True  # Assume allowed if can't check
    
    async def execute(self, intent: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute full compliance review."""
        check_result = await self.check(intent, context)
        
        # For full execution, also check robots.txt of target URLs
        urls = self._extract_urls(intent)
        robots_results = {}
        
        for url in urls:
            robots_results[url] = await self._check_robots_txt(url, "/")
        
        return {
            **check_result,
            "robots_txt_results": robots_results,
            "recommendation": "proceed" if check_result["approved"] else "review_required",
        }
    
    def _extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text."""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        return re.findall(url_pattern, text)


class WorkerAgent(BaseSpecialistAgent):
    """
    Executes browser automation tasks - form filling, data entry, navigation.
    
    This is the "hands" of the system that actually interacts with websites.
    Uses vision AI for robust element detection.
    """
    
    def __init__(
        self,
        llm: Any = None,
        browser_session: Optional["BrowserSession"] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
    ):
        super().__init__(llm, browser_session, name, description)
        self._custom_capabilities = capabilities or []
    
    @property
    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                name="form_filling",
                description="Fill out web forms with provided data",
                keywords=["fill", "form", "input", "enter"],
            ),
            AgentCapability(
                name="navigation",
                description="Navigate websites and click elements",
                keywords=["navigate", "click", "go to", "open"],
            ),
            AgentCapability(
                name="data_entry",
                description="Enter data into web applications",
                keywords=["enter", "type", "submit"],
            ),
            AgentCapability(
                name="file_operations",
                description="Upload/download files from websites",
                keywords=["upload", "download", "file"],
            ),
        ]
    
    @property
    def system_prompt(self) -> str:
        return """You are a Worker Agent specialized in browser automation.

Your capabilities:
1. Navigate to websites and interact with elements
2. Fill forms accurately with provided data
3. Handle multi-step workflows
4. Manage file uploads/downloads

Guidelines:
- Use vision to identify elements (self-healing automation)
- Verify actions completed successfully
- Handle errors gracefully with retries
- Report detailed status of each action

Be precise and methodical in your actions."""

    async def execute(self, intent: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute browser automation task."""
        logger.info(f"⚙️ Worker executing: {intent[:50]}...")
        
        agent = await self._get_browser_agent()
        
        # Build task with context
        worker_task = f"""{intent}

Available data:
{self._format_context(context)}

Instructions:
1. Navigate to the target website/page
2. Locate required fields using vision
3. Fill/interact as needed
4. Verify success
5. Report completion status"""

        try:
            agent.task = worker_task
            result = await agent.run()
            
            return {
                "status": "completed",
                "result": result.final_result() if hasattr(result, 'final_result') else str(result),
                "intent": intent,
            }
        except Exception as e:
            logger.error(f"Worker task failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "intent": intent,
            }
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dict for inclusion in prompt."""
        lines = []
        for key, value in context.items():
            if isinstance(value, dict):
                lines.append(f"{key}:")
                for k, v in value.items():
                    # Mask sensitive values
                    if any(s in k.lower() for s in ["password", "secret", "key", "token"]):
                        v = "***MASKED***"
                    lines.append(f"  {k}: {v}")
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)


# Convenience factory
def create_agent_team(
    llm: Any,
    browser_session: Optional["BrowserSession"] = None,
    include_compliance: bool = True,
) -> Dict[str, BaseSpecialistAgent]:
    """
    Create a standard team of specialist agents.
    
    Returns:
        Dict mapping agent names to agent instances
    """
    team = {
        "dispatcher": DispatcherAgent(llm=llm, browser_session=browser_session),
        "researcher": ResearcherAgent(llm=llm, browser_session=browser_session),
        "worker": WorkerAgent(llm=llm, browser_session=browser_session),
    }
    
    if include_compliance:
        team["compliance"] = ComplianceAgent(llm=llm, browser_session=browser_session)
    
    return team
