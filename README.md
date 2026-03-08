# MCP Azure Project

This project integrates Model Context Protocol (MCP) with Azure AI Foundry's Claude deployment.

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 2. Configure Azure Credentials

Edit `.env` file with your Azure AI Foundry credentials:

```bash
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_DEPLOYMENT_NAME=claude-35-sonnet
AZURE_API_VERSION=2024-10-01-preview
```

### 3. Test the MCP Server

```bash
# Start server with inspector
mcp dev server/document_server.py
# Opens browser at http://localhost:5173
```

### 4. Run the Client

```bash
python client/azure_client.py
```

## Project Structure

```
.
├── .env                    # Azure credentials (don't commit!)
├── .gitignore
├── requirements.txt
├── server/
│   ├── __init__.py
│   └── document_server.py  # MCP server with tools
├── client/
│   ├── __init__.py
│   └── azure_client.py     # Azure-compatible client
└── test_documents/
    └── sample.txt          # Test files
```

## Available Tools

- **read_document**: Read file contents
- **write_document**: Create/update files
- **list_documents**: List all documents

## Resources

- [MCP Documentation](https://modelcontextprotocol.io)
- [Azure AI Foundry](https://learn.microsoft.com/azure/ai-studio/)
- [Anthropic MCP Course](https://anthropic.skilljar.com/introduction-to-model-context-protocol)
