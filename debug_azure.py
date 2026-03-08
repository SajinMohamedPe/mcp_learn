"""
Debug script for Azure MCP Client
Test the chat functionality with detailed debugging
"""

import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from client.azure_mcp_client import AzureMCPClient


async def debug_chat():
    """Debug the chat functionality"""
    print("🐛 Starting Azure MCP Client Debug Session")
    print("=" * 50)

    try:
        async with AzureMCPClient(
            server_command="python3",
            server_args=["server/document_server.py"],
        ) as client:
            print("✅ Client initialized successfully")

            # Test a simple question that might trigger tool use
            test_question = "What documents are available?"
            print(f"\n🧪 Testing with question: '{test_question}'")

            response = await client.chat(test_question, max_iterations=3)
            print(f"\n🎯 Final response: {response}")

    except Exception as e:
        print(f"❌ Debug session failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(debug_chat())