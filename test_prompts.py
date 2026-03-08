"""
Test prompt discovery and matching
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from client.azure_mcp_client import AzureMCPClient


async def test_prompt_discovery():
    """Test that prompts are discovered and matched"""
    print("🔍 Testing Prompt Discovery & Matching")
    print("=" * 60)

    try:
        async with AzureMCPClient(
            server_command="python3",
            server_args=["server/document_server.py"],
        ) as client:
            print("\n✅ Available prompts discovered:")
            for prompt in client.available_prompts:
                print(f"   📝 {prompt['name']}")
                print(f"      → {prompt['description']}\n")
            
            print("🧪 Testing prompt matching logic:")
            print("-" * 60)
            
            test_queries = [
                "Extract action items from plan.md",
                "What are the action items in spec.txt?",
                "List legal documents",
                "Extract key tasks from the report",
            ]
            
            for query in test_queries:
                print(f"\nUser: {query}")
                
                # Test matching logic
                matching_prompts = []
                query_lower = query.lower()
                for prompt in client.available_prompts:
                    if (prompt['name'].lower().replace("_", " ") in query_lower or
                        any(word in query_lower for word in prompt['name'].lower().split("_"))):
                        matching_prompts.append(prompt)
                
                if matching_prompts:
                    print(f"✅ Matched prompts:")
                    for p in matching_prompts:
                        print(f"   → {p['name']}")
                else:
                    print(f"❌ No matching prompts")
            
            print("\n" + "=" * 60)
            print("✅ Test completed successfully!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(test_prompt_discovery())