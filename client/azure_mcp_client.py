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
        self.available_prompts = []
    
    
    async def __aenter__(self):
        """Async context manager entry - delegate to MCP client"""
        await self.mcp_client.connect()
        self.available_tools = await self.mcp_client.list_tools()
        self.available_prompts = await self.list_available_prompts()
        
        print(f"✅ Connected to MCP server")
        print(f"📦 Available tools: {[t.name for t in self.available_tools]}")
        print(f"📝 Available prompts: {[p['name'] for p in self.available_prompts]}\n")
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
    

    # list available prompts and get prompt template functions
    async def list_available_prompts(self):
        """Discover what prompts the server offers"""
        prompts = await self.mcp_client.list_prompts()
        return [{"name": p.name, "description": p.description} 
                for p in prompts]


    # Get prompt template for a specific prompt
    async def get_prompt_template(self, prompt_name: str, args: dict):
        """Retrieve a prompt template"""
        return await self.mcp_client.get_prompt(prompt_name, args)
    
    # Build system prompt that tells Claude about available tools and prompts
    def build_system_prompt(self) -> str:
        """Build system prompt that tells Claude about available tools and prompts"""
        print(f"🛠️  [SYSTEM PROMPT] Building system prompt")
        
        system_prompt = "You are a helpful assistant that can interact with a document management system.\n\n"
        
        # Add available tools
        print(f"🔧 [SYSTEM PROMPT] Adding {len(self.available_tools)} tools to system prompt")
        system_prompt += "Available Tools:\n"
        for tool in self.available_tools:
            system_prompt += f"- {tool.name}: {tool.description}\n"
            print(f"   └─ {tool.name}")
        
        # Add available prompts
        if self.available_prompts:
            print(f"📝 [SYSTEM PROMPT] Adding {len(self.available_prompts)} prompts to system prompt")
            system_prompt += "\nAvailable Prompts (use these for specialized tasks):\n"
            for prompt in self.available_prompts:
                system_prompt += f"- {prompt['name']}: {prompt['description']}\n"
                print(f"   └─ {prompt['name']}")
            system_prompt += "\nWhen a user asks for something related to these prompts, use the appropriate prompt template.\n"
        else:
            print(f"⚠️  [SYSTEM PROMPT] No prompts available to add")
        
        print(f"✅ [SYSTEM PROMPT] System prompt built (length: {len(system_prompt)} chars)\n")
        return system_prompt
    
    # Apply matching prompts to user message
    async def apply_matching_prompts(self, user_message: str, messages: list) -> list:
        """
        Detect if user message matches available prompts and apply them
        
        Args:
            user_message: The user's input
            messages: List of messages to append prompts to
        
        Returns:
            Updated messages list with prompt templates
        """
        print(f"🔍 [PROMPT FLOW] Starting prompt matching analysis")
        print(f"📌 [PROMPT FLOW] Available prompts: {[p['name'] for p in self.available_prompts]}")
        
        # Check if user message matches any available prompt
        matching_prompts = []
        user_message_lower = user_message.lower()
        print(f"📝 [PROMPT FLOW] Analyzing user message: '{user_message}'")
        
        for prompt in self.available_prompts:
            prompt_name_normalized = prompt['name'].lower().replace("_", " ")
            prompt_words = prompt['name'].lower().split("_")
            
            # Check for matches
            if prompt_name_normalized in user_message_lower:
                print(f"✅ [PROMPT FLOW] Match found: '{prompt['name']}' (full name match)")
                matching_prompts.append(prompt)
            elif any(word in user_message_lower for word in prompt_words):
                print(f"✅ [PROMPT FLOW] Match found: '{prompt['name']}' (word match)")
                matching_prompts.append(prompt)
            else:
                print(f"❌ [PROMPT FLOW] No match for '{prompt['name']}'")
        
        print(f"📊 [PROMPT FLOW] Total matching prompts: {len(matching_prompts)}")
        
        # If matching prompts found, retrieve and include them
        for prompt in matching_prompts:
            try:
                print(f"\n🎯 [PROMPT FLOW] Processing matched prompt: {prompt['name']}")
                print(f"   Description: {prompt['description']}")
                
                # Extract document ID if available (simple heuristic)
                prompt_args = {}
                words = user_message.split()
                for word in words:
                    if word.endswith((".md", ".txt", ".docx", ".pdf")):
                        prompt_args["doc_id"] = word
                        print(f"   Extracted doc_id: {word}")
                        break
                
                if not prompt_args:
                    print(f"   No document ID found in message")
                
                # Retrieve prompt template
                print(f"   → Retrieving prompt template...")
                prompt_template = await self.get_prompt_template(prompt['name'], prompt_args)
                
                # Handle prompt template - it might be a PromptMessage or string
                if isinstance(prompt_template, list):
                    # It's a list of PromptMessage objects
                    template_text = "\n".join([
                        msg.content.text if hasattr(msg.content, 'text') else str(msg.content)
                        for msg in prompt_template
                    ])
                else:
                    template_text = str(prompt_template)
                
                print(f"✅ [PROMPT FLOW] Retrieved prompt template (length: {len(template_text)} chars)")
                print(f"   Template content: {template_text[:150]}...")
                
                # Add prompt context to messages
                messages.append({
                    "role": "system",
                    "content": f"For this request, follow this prompt template:\n\n{template_text}"
                })
                print(f"✅ [PROMPT FLOW] Added prompt template to message context (total messages now: {len(messages)})")
                
            except Exception as e:
                print(f"⚠️ [PROMPT FLOW] Error retrieving prompt '{prompt['name']}': {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n🏁 [PROMPT FLOW] Prompt matching complete. Total messages: {len(messages)}")
        return messages
    

    # MCP tool and prompt methods
    async def chat(self, user_message: str, max_iterations: int = 5) -> str:
        """
        Send a message to Claude via Azure, with MCP tool and prompt support
        
        Args:
            user_message: The user's question or request
            max_iterations: Maximum number of tool call iterations
        
        Returns:
            Claude's response
        """
        print(f"\n{'='*70}")
        print(f"🚀 [CHAT FLOW] Starting new chat session")
        print(f"{'='*70}")
        
        # Build system prompt with available tools and prompts
        print(f"\n📋 [CHAT FLOW] Step 1: Building system prompt")
        system_prompt = self.build_system_prompt()
        
        print(f"📋 [CHAT FLOW] Step 2: Building message context")
        # Build messages
        messages = []
        
        # Add system prompt
        messages.append({"role": "system", "content": system_prompt})
        print(f"✅ [CHAT FLOW] Added system prompt to messages")
        
        # Apply matching prompts if any
        print(f"📋 [CHAT FLOW] Step 3: Applying matching prompts")
        messages = await self.apply_matching_prompts(user_message, messages)
        
        # Add user message
        messages.append({"role": "user", "content": user_message})
        print(f"✅ [CHAT FLOW] Added user message to context")
        
        # Convert MCP tools to Azure format
        tools = self.format_tools_for_azure()
        print(f"✅ [CHAT FLOW] Formatted {len(tools)} tools for Azure")
        
        print(f"\n📋 [CHAT FLOW] Message context built with {len(messages)} messages:")
        for i, msg in enumerate(messages):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            content_preview = content[:80] if isinstance(content, str) else str(content)[:80]
            print(f"   Message {i+1}: role='{role}', content_preview='{content_preview}...'")
        
        print(f"\n{'='*70}")
        print(f"💬 USER: {user_message}")
        print(f"{'='*70}\n")
        
        # Initial request to Claude
        print(f"📋 [CHAT FLOW] Step 4: Sending initial request to Claude")
        try:
            response = self.azure_client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto"
            )
            print(f"✅ [CHAT FLOW] Initial API call successful")
        except Exception as e:
            print(f"❌ [CHAT FLOW] Initial API call failed: {e}")
            return f"Error calling Azure OpenAI: {e}"
        
        print(f"📋 [CHAT FLOW] Step 5: Processing Claude response")
        # Handle tool calls in a loop (Claude might chain multiple tools)
        iteration = 0
        
        while iteration < max_iterations:
            print(f"� [ITERATION {iteration + 1}] Processing iteration {iteration + 1}/{max_iterations}")
            assistant_message = response.choices[0].message
            print(f"   Message preview: {assistant_message.content[:100] if assistant_message.content else 'No content'}")
            print(f"   Tool calls: {bool(assistant_message.tool_calls)}")
            
            # Check if Claude wants to use tools
            if assistant_message.tool_calls:
                print(f"🔧 [ITERATION {iteration + 1}] Claude wants to call tools")
                print(f"   Number of tools to call: {len(assistant_message.tool_calls)}")
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
                    
                    try:
                        # Execute the MCP tool
                        tool_result = await self.call_mcp_tool(tool_name, tool_args)
                        print(f"   ✅ Result: {tool_result[:100]}{'...' if len(tool_result) > 100 else ''}\n")
                    except Exception as e:
                        print(f"   ❌ Tool execution error: {e}")
                        tool_result = f"Error executing tool {tool_name}: {e}"
                    
                    # Add tool result to conversation
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result
                    })
                
                # Get Claude's next response (with tool results)
                print(f"📋 [ITERATION {iteration + 1}] Sending follow-up request with tool results to Claude")
                try:
                    response = self.azure_client.chat.completions.create(
                        model=self.deployment_name,
                        messages=messages,
                        tools=tools,
                        tool_choice="auto"
                    )
                    print(f"✅ [ITERATION {iteration + 1}] Follow-up API call successful")
                except Exception as e:
                    print(f"❌ [ITERATION {iteration + 1}] Follow-up API call failed: {e}")
                    return f"Error in follow-up API call: {e}"
                
                iteration += 1
            else:
                # No more tool calls, return final response
                print(f"✅ [ITERATION {iteration + 1}] No tool calls - ready to return response")
                final_response = assistant_message.content or "No response"
                print(f"🏁 [CHAT FLOW] Step 6: No more tool calls - returning final response")
                print(f"🔍 DEBUG: Final response: {final_response[:100]}{'...' if len(final_response) > 100 else ''}")
                print(f"✨ CLAUDE: {final_response}\n")
                print(f"{'='*70}\n")
                print(f"✅ [CHAT FLOW] Chat session completed successfully\n")
                return final_response
        
        print(f"⚠️  [CHAT FLOW] Max iterations reached ({max_iterations})")
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