
"""
MCP Configuration for Nexus Agent
Defines the default MCP servers to connect to.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import os

@dataclass
class MCPServerConfig:
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True

# Defaut servers
# Note: Ensure these are installed in your environment
# e.g. npm install -g @modelcontextprotocol/server-filesystem
MCP_SERVERS = [
    MCPServerConfig(
        name="filesystem",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "."],
        enabled=True 
    ),
    # Add more servers here
    # MCPServerConfig(
    #     name="github",
    #     command="npx",
    #     args=["-y", "@modelcontextprotocol/server-github"],
    #     env={"GITHUB_PERSONAL_ACCESS_TOKEN": os.environ.get("GITHUB_TOKEN", "")},
    #     enabled=False
    # ),
]

def get_enabled_servers() -> List[MCPServerConfig]:
    return [s for s in MCP_SERVERS if s.enabled]
