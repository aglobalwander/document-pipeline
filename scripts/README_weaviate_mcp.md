# Weaviate MCP Server Setup

This document explains how to set up and use the Weaviate MCP server with Claude Desktop.

## Overview

The Weaviate MCP (Model Context Protocol) server allows Claude to interact with a Weaviate vector database. This enables Claude to:

1. Store memories in Weaviate
2. Retrieve memories from Weaviate
3. Search the knowledge base in Weaviate

This is particularly useful for the Adaptive School Sourcebook project, as it allows Claude to search and retrieve information from the book chapters that have been ingested into Weaviate.

## Prerequisites

- Claude Desktop installed
- Python 3.11 or higher
- Weaviate client (`pip install weaviate-client`)
- MCP Python package (`pip install mcp`)
- A Weaviate instance (cloud or local)
- OpenAI API key for embeddings

## Setup

1. Clone the Weaviate MCP server repository:
   ```bash
   git clone https://github.com/weaviate/mcp-server-weaviate.git ~/Documents/Cline/MCP/mcp-server-weaviate
   ```

2. Run the setup script:
   ```bash
   python scripts/setup_weaviate_mcp.py
   ```

   This script will:
   - Create a configuration file for the Weaviate MCP server
   - Update the Claude Desktop configuration to include the Weaviate MCP server
   - Set the necessary environment variables

3. Restart Claude Desktop to apply the changes.

## Usage

Once the Weaviate MCP server is set up, Claude can use the following tools:

### 1. Store Memories

```
<use_mcp_tool>
<server_name>weaviate</server_name>
<tool_name>weaviate-store-memory</tool_name>
<arguments>
{
  "information": "The Adaptive School is a book by Robert J. Garmston and Bruce M. Wellman."
}
</arguments>
</use_mcp_tool>
```

### 2. Find Memories

```
<use_mcp_tool>
<server_name>weaviate</server_name>
<tool_name>weaviate-find-memories</tool_name>
<arguments>
{
  "query": "Who wrote The Adaptive School?"
}
</arguments>
</use_mcp_tool>
```

### 3. Search Knowledge Base

```
<use_mcp_tool>
<server_name>weaviate</server_name>
<tool_name>weaviate-search-knowledge</tool_name>
<arguments>
{
  "query": "What is an adaptive school?"
}
</arguments>
</use_mcp_tool>
```

## Troubleshooting

If you encounter issues with the Weaviate MCP server:

1. Check that the Weaviate instance is accessible
2. Verify that the API keys are correct
3. Ensure that the collections exist in Weaviate
4. Check the Claude Desktop logs for errors

## Next Steps

After setting up the Weaviate MCP server, you can:

1. Ingest the Adaptive School Sourcebook chapters into Weaviate
2. Create a script to query the Adaptive School collection
3. Develop a summarization tool for the Adaptive School content
