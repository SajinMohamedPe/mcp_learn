"""
Main CLI for Azure MCP Client
Interactive chat interface with Claude and MCP tool support
"""

import asyncio
import sys
import os
from typing import List, Optional
from datetime import datetime
from client.azure_mcp_client import AzureMCPClient


class MainCLI:
    """
    Main CLI interface for Azure MCP Client
    Provides interactive chat with Claude and MCP tool integration
    """

    def __init__(
        self,
        server_command: str = "python3",
        server_args: Optional[List[str]] = None,
        max_iterations: int = 5
    ):
        """
        Initialize the CLI

        Args:
            server_command: Command to run the MCP server
            server_args: Arguments for the MCP server
            max_iterations: Maximum tool call iterations per message
        """
        if server_args is None:
            server_args = ["server/document_server.py"]

        self.server_command = server_command
        self.server_args = server_args
        self.max_iterations = max_iterations

        self.client: Optional[AzureMCPClient] = None
        self.conversation_history: List[dict] = []
        self.session_start_time = datetime.now()

    async def initialize_client(self):
        """Initialize and connect the Azure MCP client"""
        print("🚀 Initializing Azure MCP Client...")
        print(f"📡 Server command: {self.server_command}")
        print(f"📡 Server args: {self.server_args}")
        print()

        self.client = AzureMCPClient(
            server_command=self.server_command,
            server_args=self.server_args
        )

        # Connect to the MCP server
        await self.client.__aenter__()

    async def cleanup_client(self):
        """Clean up the client connection"""
        if self.client:
            await self.client.__aexit__(None, None, None)

    def show_welcome(self):
        """Display welcome message and help"""
        print("🤖 Azure MCP Chat Interface")
        print("=" * 50)
        print("💡 Ask questions about your documents using Claude + MCP tools")
        print()
        print("📚 Available commands:")
        print("  /help     - Show this help message")
        print("  /history  - Show conversation history")
        print("  /tools    - List available MCP tools")
        print("  /clear    - Clear conversation history")
        print("  /quit     - Exit the chat")
        print()
        print("💬 Just type your questions normally to chat with Claude!")
        print("-" * 50)

    def show_help(self):
        """Show detailed help"""
        print("\n📖 Help - Azure MCP Chat Commands")
        print("=" * 40)
        print("/help     - Show this help message")
        print("/history  - Show conversation history")
        print("/tools    - List available MCP tools")
        print("/clear    - Clear conversation history")
        print("/quit     - Exit the chat")
        print()
        print("💡 Tips:")
        print("• Claude can use MCP tools to read/edit documents")
        print("• Ask questions like 'Read the spec.txt file'")
        print("• Use @doc_id to reference specific documents")
        print("• Type normally for regular chat")

    async def show_tools(self):
        """Display available MCP tools"""
        if not self.client or not self.client.available_tools:
            print("❌ No tools available - client not initialized")
            return

        print("\n🔧 Available MCP Tools")
        print("=" * 30)
        for tool in self.client.available_tools:
            print(f"📋 {tool.name}")
            print(f"   {tool.description}")
            print()

    def show_history(self):
        """Display conversation history"""
        if not self.conversation_history:
            print("📝 No conversation history yet")
            return

        print("\n📜 Conversation History")
        print("=" * 30)
        for i, entry in enumerate(self.conversation_history, 1):
            timestamp = entry['timestamp'].strftime('%H:%M:%S')
            print(f"{i}. [{timestamp}] {entry['role'].upper()}: {entry['content'][:100]}{'...' if len(entry['content']) > 100 else ''}")
        print()

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history.clear()
        print("🧹 Conversation history cleared")

    def add_to_history(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append({
            'timestamp': datetime.now(),
            'role': role,
            'content': content
        })

    async def process_command(self, command: str) -> bool:
        """
        Process a command (starts with /)

        Returns:
            True if should continue, False if should exit
        """
        cmd = command.lower().strip()

        if cmd == '/help':
            self.show_help()
        elif cmd == '/history':
            self.show_history()
        elif cmd == '/tools':
            await self.show_tools()
        elif cmd == '/clear':
            self.clear_history()
        elif cmd in ['/quit', '/exit', '/q']:
            return False
        else:
            print(f"❓ Unknown command: {command}")
            print("Type /help for available commands")

        return True

    async def process_question(self, question: str):
        """Process a regular question/chat message"""
        if not self.client:
            print("❌ Client not initialized")
            return

        # Add to history
        self.add_to_history('user', question)

        try:
            # Get response from Claude
            response = await self.client.chat(question, max_iterations=self.max_iterations)

            # Add response to history
            self.add_to_history('assistant', response)

        except Exception as e:
            error_msg = f"❌ Error processing question: {e}"
            print(error_msg)
            self.add_to_history('system', error_msg)

    async def interactive_loop(self):
        """Main interactive loop"""
        self.show_welcome()

        try:
            while True:
                try:
                    # Get user input
                    user_input = input("\n❓ You: ").strip()

                    if not user_input:
                        continue

                    # Check if it's a command
                    if user_input.startswith('/'):
                        should_continue = await self.process_command(user_input)
                        if not should_continue:
                            break
                    else:
                        # Process as regular question
                        await self.process_question(user_input)

                except KeyboardInterrupt:
                    print("\n👋 Goodbye!")
                    break
                except EOFError:
                    print("\n👋 Goodbye!")
                    break

        finally:
            await self.cleanup_client()

    async def run_once(self, question: str):
        """Run a single question and exit"""
        try:
            await self.initialize_client()
            await self.process_question(question)
        finally:
            await self.cleanup_client()

    async def run(self):
        """Main run method - determines mode based on arguments"""
        await self.initialize_client()

        if len(sys.argv) > 1:
            # Command line mode: python main.py "your question here"
            question = " ".join(sys.argv[1:])
            await self.run_once(question)
        else:
            # Interactive mode
            await self.interactive_loop()


async def main():
    """Entry point"""
    cli = MainCLI()
    await cli.run()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)