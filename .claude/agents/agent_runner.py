"""Agent runner for executing document processing workflows."""
import asyncio
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from orchestration.orchestrator import Orchestrator
from specialized.document_processor_agent import DocumentProcessorAgent
from specialized.mcp_bridge_agent import MCPBridgeAgent
from specialized.storage_agent import StorageAgent
from specialized.transformer_agent import TransformerAgent


class AgentRunner:
    """Main runner for agent-based document processing."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize agent runner.
        
        Args:
            config: Runner configuration
        """
        self.config = config or {}
        self.orchestrator = None
        self.agents = {}
        self.logger = logging.getLogger("agent_runner")
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
    async def initialize(self):
        """Initialize all agents and orchestrator."""
        self.logger.info("Initializing agent runner...")
        
        # Create orchestrator
        self.orchestrator = Orchestrator(config=self.config.get("orchestrator", {}))
        await self.orchestrator.initialize()
        
        # Create and register agents
        agents_config = self.config.get("agents", {})
        
        # Document processor agent
        doc_processor = DocumentProcessorAgent(
            config=agents_config.get("document_processor", {})
        )
        await doc_processor.initialize()
        self.agents["document_processor"] = doc_processor
        
        # MCP bridge agent
        mcp_bridge = MCPBridgeAgent(
            config=agents_config.get("mcp_bridge", {})
        )
        await mcp_bridge.initialize()
        self.agents["mcp_bridge"] = mcp_bridge
        
        # Storage agent
        storage = StorageAgent(
            config=agents_config.get("storage", {})
        )
        await storage.initialize()
        self.agents["storage"] = storage
        
        # Transformer agent
        transformer = TransformerAgent(
            config=agents_config.get("transformer", {})
        )
        await transformer.initialize()
        self.agents["transformer"] = transformer
        
        # Register agents with orchestrator
        for name, agent in self.agents.items():
            await self.orchestrator._register_agent({
                "name": name,
                "class": type(agent),
                "config": agent.config
            })
        
        self.logger.info("Agent runner initialized successfully")
        
    async def process_document(
        self,
        document_path: str,
        pipeline_type: str = "markdown",
        **kwargs
    ) -> Dict[str, Any]:
        """Process a document using agent-based pipeline.
        
        Args:
            document_path: Path to document
            pipeline_type: Type of pipeline (text, markdown, json, weaviate)
            **kwargs: Additional pipeline configuration
            
        Returns:
            Processing results
        """
        # Create workflow
        workflow_config = {
            "document_path": document_path,
            "pipeline_config": {
                "pipeline_type": pipeline_type,
                **kwargs
            }
        }
        
        # Send create workflow message
        create_msg = await self.orchestrator.process({
            "sender": "runner",
            "recipient": "orchestrator",
            "action": "create_workflow",
            "payload": workflow_config
        })
        
        workflow_id = create_msg.payload.get("workflow_id")
        
        # Execute workflow
        execute_msg = await self.orchestrator.process({
            "sender": "runner",
            "recipient": "orchestrator",
            "action": "execute_workflow",
            "payload": {"workflow_id": workflow_id}
        })
        
        return execute_msg.payload
    
    async def process_batch(
        self,
        document_paths: List[str],
        pipeline_type: str = "markdown",
        concurrent: int = 3,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Process multiple documents concurrently.
        
        Args:
            document_paths: List of document paths
            pipeline_type: Type of pipeline
            concurrent: Number of concurrent processes
            **kwargs: Additional pipeline configuration
            
        Returns:
            List of processing results
        """
        semaphore = asyncio.Semaphore(concurrent)
        
        async def process_with_limit(path):
            async with semaphore:
                return await self.process_document(path, pipeline_type, **kwargs)
        
        tasks = [process_with_limit(path) for path in document_paths]
        results = await asyncio.gather(*tasks)
        
        return results
    
    async def get_status(self) -> Dict[str, Any]:
        """Get status of all agents.
        
        Returns:
            Status information
        """
        status = {
            "orchestrator": self.orchestrator.get_status_report() if self.orchestrator else None,
            "agents": {}
        }
        
        for name, agent in self.agents.items():
            status["agents"][name] = agent.get_status_report()
        
        return status
    
    async def shutdown(self):
        """Shutdown all agents."""
        self.logger.info("Shutting down agent runner...")
        
        # Shutdown all agents
        for name, agent in self.agents.items():
            await agent.shutdown()
        
        # Shutdown orchestrator
        if self.orchestrator:
            await self.orchestrator.shutdown()
        
        self.logger.info("Agent runner shutdown complete")


async def main():
    """Example usage of agent runner."""
    # Configuration
    config = {
        "orchestrator": {
            "max_concurrent_workflows": 5
        },
        "agents": {
            "document_processor": {
                "docling": {
                    "ocr_mode": "hybrid",
                    "extract_tables": True
                },
                "pymupdf": {
                    "extract_images": False
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
    
    # Create runner
    runner = AgentRunner(config)
    
    try:
        # Initialize
        await runner.initialize()
        
        # Process a document
        result = await runner.process_document(
            document_path="/path/to/document.pdf",
            pipeline_type="markdown",
            ocr_mode="hybrid",
            extract_tables=True
        )
        
        print(f"Processing result: {result}")
        
        # Get status
        status = await runner.get_status()
        print(f"System status: {status}")
        
    finally:
        # Cleanup
        await runner.shutdown()


if __name__ == "__main__":
    asyncio.run(main())