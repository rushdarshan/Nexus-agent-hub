
import asyncio
from unittest.mock import MagicMock, patch
import sys

# Mock modules before importing intelligent_router
sys.modules['mcp_config'] = MagicMock()
sys.modules['browser_use.mcp.client'] = MagicMock()
sys.modules['browser_use.tools.service'] = MagicMock()

# Now import
from intelligent_router import NexusRouter

# Mock LLM
class MockLLM:
    pass

async def main():
    print("🧪 Verifying MCP Integration (Mocked)...")
    
    # Mock the Agent class to inspect tools
    with patch('intelligent_router.Agent') as MockAgent:
        # Setup mock return
        instance = MockAgent.return_value
        instance.run.return_value = MagicMock(final_result=lambda: "Mock Success")
        
        # Mock the context manager for AsyncExitStack if needed, 
        # but since we mocked mcp.client, the import inside _run_browser will use the mock
        
        from browser_use.mcp.client import MCPClient
        # Setup MCPClient mock to be an async context manager
        mock_client_instance = MCPClient.return_value
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        
        router = NexusRouter(llm=MockLLM())
        
        # Trigger the browser run
        print("   Running router.execute('read file')...")
        
        # We force the router to choose 'browser'
        with patch.object(router, 'route_task') as mock_route:
            mock_route.return_value = type('obj', (object,), {
                'platform': 'browser',
                'reasoning': 'test',
                'steps': ['read file']
            })()
            
            # Helper to mock get_enabled_servers
            with patch('mcp_config.get_enabled_servers') as mock_get_servers:
                mock_get_servers.return_value = [
                    type('obj', (object,), {'name': 'test-server', 'command': 'echo', 'args': [], 'env': {}})()
                ]
                
                await router.execute("read file")
            
        # Check if Agent was called
        if MockAgent.call_count == 1:
            print("✅ Agent was instantiated.")
            
            # Check arguments
            args, kwargs = MockAgent.call_args
            tools = kwargs.get('tools')
            
            if tools:
                print(f"✅ Tools provided to Agent: {tools}")
                print("✅ MCP Integration logic verified (Mocked)")
            else:
                print("❌ No tools provided to Agent!")
        else:
             print("❌ Agent was NOT instantiated.")

if __name__ == "__main__":
    asyncio.run(main())
