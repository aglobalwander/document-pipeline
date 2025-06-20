#!/usr/bin/env python3
"""
Script to set up the Weaviate MCP server configuration.
"""

import os
import json
import sys

# Load configuration from environment variables
from dotenv import load_dotenv
load_dotenv()

# Define the configuration
weaviate_config = {
    "weaviateUrl": os.getenv("WEAVIATE_URL", "http://localhost:8080"),
    "weaviateApiKey": os.getenv("WEAVIATE_API_KEY", ""),
    "openaiApiKey": os.getenv("OPENAI_API_KEY", ""),
    "searchCollectionName": os.getenv("WEAVIATE_SEARCH_COLLECTION", "AdaptiveSchools"),
    "storeCollectionName": os.getenv("WEAVIATE_STORE_COLLECTION", "AdaptiveSchoolsMemories")
}

# Validate required environment variables
if not weaviate_config["weaviateApiKey"]:
    print("Error: WEAVIATE_API_KEY environment variable is not set")
    sys.exit(1)
if not weaviate_config["openaiApiKey"]:
    print("Error: OPENAI_API_KEY environment variable is not set")
    sys.exit(1)

# Path to the MCP server repository
mcp_repo_path = os.path.expanduser("~/Documents/Cline/MCP/mcp-server-weaviate")

# Check if the repository exists
if not os.path.exists(mcp_repo_path):
    print(f"Error: MCP server repository not found at {mcp_repo_path}")
    print("Please clone the repository first:")
    print("git clone https://github.com/weaviate/mcp-server-weaviate.git ~/Documents/Cline/MCP/mcp-server-weaviate")
    sys.exit(1)

# Save the Weaviate configuration
config_path = os.path.join(mcp_repo_path, "weaviate-config.json")
with open(config_path, 'w') as f:
    json.dump(weaviate_config, f, indent=2)
print(f"Weaviate configuration saved to {config_path}")

# Path to Claude Desktop configuration
claude_config_path = os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json")

# Check if Claude Desktop configuration exists
if not os.path.exists(claude_config_path):
    print(f"Error: Claude Desktop configuration not found at {claude_config_path}")
    print("Please make sure Claude Desktop is installed and has been run at least once.")
    sys.exit(1)

# Load the existing Claude Desktop configuration
try:
    with open(claude_config_path, 'r') as f:
        claude_config = json.load(f)
except Exception as e:
    print(f"Error loading Claude Desktop configuration: {e}")
    sys.exit(1)

# Ensure mcpServers key exists
if "mcpServers" not in claude_config:
    claude_config["mcpServers"] = {}

# Add or update the Weaviate MCP server configuration
claude_config["mcpServers"]["weaviate"] = {
    "command": "python",
    "args": [
        "-m",
        "src.server",
        "--weaviate-url",
        weaviate_config["weaviateUrl"],
        "--weaviate-api-key",
        weaviate_config["weaviateApiKey"],
        "--search-collection-name",
        weaviate_config["searchCollectionName"],
        "--store-collection-name",
        weaviate_config["storeCollectionName"],
        "--openai-api-key",
        weaviate_config["openaiApiKey"]
    ],
    "env": {
        "PYTHONPATH": mcp_repo_path
    }
}

# Save the updated Claude Desktop configuration
try:
    with open(claude_config_path, 'w') as f:
        json.dump(claude_config, f, indent=2)
    print(f"Claude Desktop configuration updated at {claude_config_path}")
    print("Weaviate MCP server has been added to Claude Desktop configuration.")
    print("\nTo use the Weaviate MCP server:")
    print("1. Restart Claude Desktop")
    print("2. In a conversation, you can use the Weaviate MCP server with:")
    print("   - use_mcp_tool with server_name='weaviate'")
    print("   - Available tools: weaviate-store-memory, weaviate-find-memories, weaviate-search-knowledge")
except Exception as e:
    print(f"Error saving Claude Desktop configuration: {e}")
    sys.exit(1)
