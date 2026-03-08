"""
Complete MCP + Azure demo
Demonstrates tools, resources, and prompts
"""

import asyncio
from client.azure_client import AzureMCPClient


async def demo():
    """Run complete MCP demo"""
    
    client = AzureMCPClient()
    server_path = "server/document_server.py"
    
    async with await client.connect_to_server(server_path):
        
        print("=== DEMO 1: Using Tools ===\n")
        
        # Claude uses tools automatically
        await client.chat(
            "Create a document called 'project_plan.txt' with a simple "
            "project plan for building an MCP server"
        )
        
        await client.chat("Now read that project plan back to me")
        
        
        print("\n=== DEMO 2: Using Resources ===\n")
        
        # List available resources
        resources = await client.list_resources()
        print(f"Available resources: {[r.name for r in resources]}")
        
        # Read a resource directly (app-controlled)
        if resources:
            content = await client.read_resource(resources[0].uri)
            print(f"Resource content preview: {content[:100]}...")
        
        
        print("\n=== DEMO 3: Using Prompts ===\n")
        
        # Get prompt template
        prompt_text = await client.get_prompt(
            "format_document",
            {"filename": "project_plan.txt"}
        )
        
        print(f"Using prompt: {prompt_text[:100]}...\n")
        
        # Execute the prompt
        await client.chat(prompt_text)
        
        
        print("\n=== DEMO 4: Complex Multi-Step Task ===\n")
        
        await client.chat(
            "Create a meeting agenda with 5 topics, save it as 'agenda.txt', "
            "then create a summary of that agenda in 'agenda_summary.txt'"
        )


if __name__ == "__main__":
    asyncio.run(demo())
