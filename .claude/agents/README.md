# Agent-Driven Document Processing Architecture

## Overview

This agent-driven architecture transforms the document processing pipeline into a distributed, intelligent system where specialized agents collaborate to handle different aspects of document processing. This approach leverages Claude Code for orchestration and MCP servers for enhanced capabilities.

## Architecture Components

### Core Components

1. **Base Agent** (`core/base_agent.py`)
   - Foundation for all agents
   - Handles messaging, status management, and capabilities
   - Provides async processing interface

2. **Orchestrator** (`orchestration/orchestrator.py`)
   - Central coordinator for all agents
   - Manages workflows and agent interactions
   - Plans and executes document processing pipelines
   - Monitors workflow execution

### Specialized Agents

1. **Document Processor Agent** (`specialized/document_processor_agent.py`)
   - Handles PDF, DOCX, PPTX processing
   - Integrates Enhanced Docling, PyMuPDF, Mammoth, MarkItDown
   - Provides document analysis capabilities

2. **MCP Bridge Agent** (`specialized/mcp_bridge_agent.py`)
   - Bridges to external MCP servers
   - Integrates GitHub, Weaviate, Playwright, Context7, Wolfram
   - Enables web scraping, library docs, and computational queries

3. **Storage Agent** (`specialized/storage_agent.py`)
   - Manages document persistence
   - Handles Weaviate vector storage
   - Provides file system and cache storage

4. **Transformer Agent** (`specialized/transformer_agent.py`)
   - Converts between formats (text, markdown, JSON, CSV, Excel)
   - Handles document chunking
   - Enriches documents with metadata

## Key Features

### 1. Distributed Processing
- Agents operate independently and asynchronously
- Parallel processing of multiple documents
- Scalable architecture

### 2. MCP Integration
- Seamless integration with MCP servers
- Access to external services and tools
- Enhanced capabilities through MCP ecosystem

### 3. Workflow Management
- Dynamic workflow creation based on document type
- Dependency management between steps
- Progress monitoring and error handling

### 4. Flexible Storage
- Multiple storage backends (Weaviate, file system, cache)
- Vector search capabilities
- Document versioning and caching

## Usage

### Basic Example

```python
from .claude.agents.agent_runner import AgentRunner

# Initialize runner
runner = AgentRunner(config={
    "agents": {
        "document_processor": {
            "docling": {"ocr_mode": "hybrid"}
        },
        "mcp_bridge": {
            "mcp_servers": {
                "github": {"enabled": True},
                "weaviate": {"enabled": True}
            }
        }
    }
})

await runner.initialize()

# Process a document
result = await runner.process_document(
    document_path="/path/to/document.pdf",
    pipeline_type="markdown",
    ocr_mode="hybrid",
    extract_tables=True
)

await runner.shutdown()
```

### Batch Processing

```python
# Process multiple documents concurrently
results = await runner.process_batch(
    document_paths=[
        "/path/to/doc1.pdf",
        "/path/to/doc2.docx",
        "/path/to/doc3.pptx"
    ],
    pipeline_type="json",
    concurrent=3
)
```

## Workflow Examples

### PDF to Weaviate Workflow

1. **Load** - Loader agent reads PDF file
2. **Process** - Document processor uses Enhanced Docling
3. **Transform** - Transformer chunks the text
4. **Store** - Storage agent saves to Weaviate

### Web Documentation Workflow

1. **Scrape** - MCP bridge uses Playwright to scrape web page
2. **Process** - Document processor extracts content
3. **Transform** - Transformer converts to markdown
4. **Enrich** - Transformer adds metadata
5. **Store** - Storage agent saves to file system

## Agent Communication

Agents communicate through structured messages:

```python
message = AgentMessage(
    sender="orchestrator",
    recipient="document_processor",
    action="process_pdf_docling",
    payload={
        "file_path": "/path/to/document.pdf",
        "ocr_mode": "hybrid"
    },
    correlation_id="workflow_123"
)
```

## Configuration

### Agent Configuration

```python
config = {
    "orchestrator": {
        "max_concurrent_workflows": 5
    },
    "agents": {
        "document_processor": {
            "docling": {
                "ocr_mode": "hybrid",
                "extract_tables": True
            }
        },
        "mcp_bridge": {
            "mcp_servers": {
                "github": {"enabled": True},
                "weaviate": {"enabled": True},
                "context7": {"enabled": True}
            }
        },
        "storage": {
            "weaviate_url": "http://localhost:8080",
            "default_collection": "Documents"
        },
        "transformer": {
            "chunk_size": 1000,
            "chunk_overlap": 200
        }
    }
}
```

## Benefits of Agent Architecture

1. **Modularity** - Each agent has a specific responsibility
2. **Scalability** - Agents can be distributed across machines
3. **Flexibility** - Easy to add new agents or capabilities
4. **Resilience** - Failure isolation and recovery
5. **Extensibility** - MCP integration enables unlimited extensions

## Integration with Existing Pipeline

The agent architecture can work alongside your existing pipeline:

1. **Gradual Migration** - Start with specific document types
2. **Hybrid Mode** - Use agents for complex workflows
3. **Backwards Compatible** - Existing scripts continue to work
4. **Enhanced Capabilities** - Add MCP features incrementally

## Future Enhancements

1. **Agent Discovery** - Dynamic agent registration
2. **Load Balancing** - Distribute work across agent instances
3. **Event Streaming** - Real-time workflow updates
4. **Agent Templates** - Reusable agent configurations
5. **Visual Workflow Designer** - GUI for creating workflows
6. **Performance Monitoring** - Agent metrics and profiling

## Best Practices

1. **Keep Agents Focused** - Single responsibility principle
2. **Use Async Processing** - Non-blocking operations
3. **Handle Failures Gracefully** - Implement retry logic
4. **Log Extensively** - Track agent activities
5. **Test Independently** - Unit test each agent
6. **Document Capabilities** - Clear agent descriptions

## Troubleshooting

### Common Issues

1. **Agent Not Responding**
   - Check agent status
   - Verify initialization completed
   - Review logs for errors

2. **Workflow Stuck**
   - Monitor workflow state
   - Check agent dependencies
   - Verify MCP connections

3. **Performance Issues**
   - Adjust concurrent processing limits
   - Optimize chunk sizes
   - Enable caching

## Conclusion

This agent-driven architecture provides a powerful, flexible foundation for document processing that leverages the best of Claude Code, MCP servers, and your existing processing capabilities. The modular design enables easy extension and adaptation to new requirements while maintaining reliability and performance.