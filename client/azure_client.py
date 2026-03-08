"""
MCP Client that connects Claude (via Azure) to MCP servers
"""

import asyncio
import os
import json
from typing import Optional
from dotenv import load_dotenv
from openai import AzureOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load environment variables
load_dotenv()


class AzureMCPClient:
    """
    MCP Client for Azure AI Foundry + Claude
    Handles communication between Azure Claude and MCP servers
    """
    
    def __init__(self):
        # Azure OpenAI client setup
        self.azure_client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_API_VERSION", "2024-10-01-preview")
        )
        self.deployment_name = os.getenv("AZURE_DEPLOYMENT_NAME")
        
        # MCP session (will be initialized when connecting to server)
        self.session: Optional[ClientSession] = None
        self.available_tools = []
    
    async def connect_to_server(self, server_script_path: str):
        """
        Connect to an MCP server running locally
        
        Args:
            server_script_path: Path to the MCP server Python script
        """
        server_params = StdioServerParameters(
            command="python",
            args=[server_script_path],
            env=None
        )
        
        stdio_transport = await stdio_client(server_params)
        self.stdio, self.write = stdio_transport
        
        async with ClientSession(self.stdio, self.write) as session:
            self.session = session
            
            # Initialize the session
            await session.initialize()
            
            # Get available tools from the server
            tools_response = await session.list_tools()
            self.available_tools = tools_response.tools
            
            print(f"Connected to MCP server. Available tools: {[t.name for t in self.available_tools]}")
            
            return session
    
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
        if not self.session:
            raise RuntimeError("Not connected to MCP server. Call connect_to_server() first.")
        
        result = await self.session.call_tool(tool_name, tool_args)
        
        # Extract text content from result
        if result.content:
            return "\n".join([
                item.text for item in result.content 
                if hasattr(item, 'text')
            ])
        return "No result"
    
    async def chat(self, user_message: str) -> str:
        """
        Send a message to Claude via Azure, with MCP tool support
        """
        messages = [{"role": "user", "content": user_message}]
        
        # Convert MCP tools to Azure format
        tools = self.format_tools_for_azure()
        
        print(f"\n{'='*60}")
        print(f"USER: {user_message}")
        print(f"{'='*60}\n")
        
        # Initial request to Claude
        response = self.azure_client.chat.completions.create(
            model=self.deployment_name,
            messages=messages,
            tools=tools if tools else None,
            tool_choice="auto"
        )
        
        # Handle tool calls in a loop
        max_iterations = 5
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
                    
                    print(f"   Result: {tool_result[:100]}{'...' if len(tool_result) > 100 else ''}\n")
                    
                    # Add tool result to conversation
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result
                    })
                
                # Get Claude's next response
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
                print(f"💬 CLAUDE: {final_response}\n")
                return final_response
        
        return "Max iterations reached"
    
    async def list_resources(self):
        """List available resources from MCP server"""
        if not self.session:
            raise RuntimeError("Not connected to MCP server")
        
        resources_response = await self.session.list_resources()
        return resources_response.resources
    
    async def read_resource(self, uri: str) -> str:
        """Read a specific resource"""
        if not self.session:
            raise RuntimeError("Not connected to MCP server")
        
        resource_content = await self.session.read_resource(uri)
        
        # Extract text content
        if resource_content.contents:
            return "\n".join([
                item.text for item in resource_content.contents
                if hasattr(item, 'text')
            ])
        return "No content"
    
    async def get_prompt(self, prompt_name: str, arguments: dict) -> str:
        """Get a prompt template from the server"""
        if not self.session:
            raise RuntimeError("Not connected to MCP server")
        
        prompt_result = await self.session.get_prompt(prompt_name, arguments)
        
        # Extract the prompt text
        if prompt_result.messages:
            return prompt_result.messages[0].content.text
        return ""


async def main():
    """
    Example usage of Azure MCP Client
    """
    client = AzureMCPClient()
    
    # Connect to the MCP server
    server_path = "server/document_server.py"
    
    async with await client.connect_to_server(server_path):
        # Example conversations
        
        # 1. List documents
        await client.chat("What documents are available?")
        
        # 2. Create a document
        await client.chat("Create a file called 'meeting_notes.txt' with the content: 'Team meeting on Azure MCP integration. Action items: 1. Test tools 2. Deploy to production'")
        
        # 3. Read the document
        await client.chat("Read the meeting notes file")
        
        # 4. Complex multi-step task
        await client.chat("Create a todo list file with 3 tasks, then read it back to confirm")


if __name__ == "__main__":
    asyncio.run(main())
