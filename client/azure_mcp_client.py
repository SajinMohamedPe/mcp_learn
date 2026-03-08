"""
Azure MCP Client - Integrates MCP with Azure AI Foundry Claude
"""

import os
import json
from typing import Optional
from dotenv import load_dotenv
from openai import AzureOpenAI
try:
    from .mcp_client import MCPClient
except ImportError:
    from mcp_client import MCPClient

load_dotenv()


class AzureMCPClient:
    """
    MCP Client for Azure AI Foundry + Claude
    Combines MCPClient (for MCP servers) with Azure OpenAI (for Claude)
    """
    
    def __init__(self, server_command: str, server_args: list[str]):
        # Azure OpenAI client setup
        self.azure_client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_API_VERSION", "2024-10-01-preview")
        )
        self.deployment_name = os.getenv("AZURE_DEPLOYMENT_NAME")
        
        # MCP client setup
        self.mcp_client = MCPClient(
            command=server_command,
            args=server_args
        )
        
        self.available_tools = []
    
    
    async def __aenter__(self):
        """Async context manager entry - delegate to MCP client"""
        await self.mcp_client.connect()
        self.available_tools = await self.mcp_client.list_tools()
        print(f"✅ Connected to MCP server")
        print(f"📦 Available tools: {[t.name for t in self.available_tools]}\n")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - delegate to MCP client"""
        await self.mcp_client.cleanup()
    

    
    def format_tools_for_azure(self) -> list[dict]:
        """
        Convert MCP tools to Azure OpenAI function calling format
        """
        azure_tools = []
        
        for tool in self.available_tools:
            azure_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            }
            azure_tools.append(azure_tool)
        
        return azure_tools
    
    async def call_mcp_tool(self, tool_name: str, tool_args: dict) -> str:
        """
        Execute an MCP tool and return the result
        """
        result = await self.mcp_client.call_tool(tool_name, tool_args)
        
        # Extract text content from result
        if result and result.content:
            return "\n".join([
                item.text for item in result.content 
                if hasattr(item, 'text')
            ])
        return "No result"
    
    async def chat(self, user_message: str, max_iterations: int = 5) -> str:
        """
        Send a message to Claude via Azure, with MCP tool support
        
        Args:
            user_message: The user's question or request
            max_iterations: Maximum number of tool call iterations
        
        Returns:
            Claude's response
        """
        messages = [{"role": "user", "content": user_message}]
        
        # Convert MCP tools to Azure format
        tools = self.format_tools_for_azure()
        
        print(f"\n{'='*70}")
        print(f"💬 USER: {user_message}")
        print(f"{'='*70}\n")
        
        # Initial request to Claude
        response = self.azure_client.chat.completions.create(
            model=self.deployment_name,
            messages=messages,
            tools=tools if tools else None,
            tool_choice="auto"
        )
        
        # Handle tool calls in a loop (Claude might chain multiple tools)
        iteration = 0
        
        while iteration < max_iterations:
            assistant_message = response.choices[0].message
            
            # Check if Claude wants to use tools
            if assistant_message.tool_calls:
                # Add assistant's message to conversation
                messages.append({
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in assistant_message.tool_calls
                    ]
                })
                
                # Execute each tool call
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    print(f"🔧 Claude is calling tool: {tool_name}")
                    print(f"   Arguments: {tool_args}")
                    
                    # Execute the MCP tool
                    tool_result = await self.call_mcp_tool(tool_name, tool_args)
                    
                    print(f"   ✅ Result: {tool_result[:100]}{'...' if len(tool_result) > 100 else ''}\n")
                    
                    # Add tool result to conversation
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result
                    })
                
                # Get Claude's next response (with tool results)
                response = self.azure_client.chat.completions.create(
                    model=self.deployment_name,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto"
                )
                
                iteration += 1
            else:
                # No more tool calls, return final response
                final_response = assistant_message.content or "No response"
                print(f"✨ CLAUDE: {final_response}\n")
                print(f"{'='*70}\n")
                return final_response
        
        return "⚠️  Max iterations reached"


# Test function
async def main():
    import asyncio
    
    async with AzureMCPClient(
        server_command="python3",
        server_args=["server/document_server.py"],
    ) as client:
        # Test chat with MCP tool calling
        response = await client.chat("Read the spec.txt document and tell me what it contains")
        print(response)


if __name__ == "__main__":
    import asyncio
    import sys
    
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main())