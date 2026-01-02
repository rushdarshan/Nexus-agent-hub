"""
Android-Use: AI-powered Android automation
============================================

A browser-use inspired framework for Android device automation using AI vision.

Quick Start:
    from android_use import AndroidAgent, Device
    
    async def main():
        agent = AndroidAgent(task="Open Settings and enable WiFi")
        result = await agent.run()
        print(result.success)

Or use the convenience function:
    from android_use import run_android_task
    
    result = await run_android_task("Open Chrome and search for Python")
"""

import logging
from importlib.metadata import version, PackageNotFoundError

# Version
try:
    __version__ = version("android-use")
except PackageNotFoundError:
    __version__ = "1.0.0"

# Set up logging
logger = logging.getLogger('android_use')
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Core imports
from .device.device import Device, DeviceConfig, DeviceInfo
from .controller.controller import AndroidController, controller, ActionCategory
from .agent.agent import AndroidAgent, AgentConfig, AgentResult, AgentStatus, run_android_task
from .hierarchy.hierarchy import ViewHierarchy, AndroidElement
from .llm.llm import LLM, LLMConfig, LLMProvider

# Config
from .config import AndroidUseConfig, get_config, update_config

# Convenience re-exports
from .server.server import create_app, run_server

__all__ = [
    # Version
    '__version__',
    
    # Core Classes
    'Device',
    'DeviceConfig', 
    'DeviceInfo',
    'AndroidController',
    'controller',
    'ActionCategory',
    'AndroidAgent',
    'AgentConfig',
    'AgentResult',
    'AgentStatus',
    
    # Hierarchy
    'ViewHierarchy',
    'AndroidElement',
    
    # LLM
    'LLM',
    'LLMConfig',
    'LLMProvider',
    
    # Config
    'AndroidUseConfig',
    'get_config',
    'update_config',
    
    # Server
    'create_app',
    'run_server',
    
    # Convenience
    'run_android_task',
]

