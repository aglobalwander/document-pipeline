"""Main orchestrator for agent-based document processing."""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from pathlib import Path
import uuid
import json
from dataclasses import dataclass, field
from enum import Enum

from ..core.base_agent import (
    BaseAgent, AgentRole, AgentStatus, AgentMessage, AgentCapability
)


class WorkflowState(Enum):
    """Workflow execution states."""
    PLANNING = "planning"
    EXECUTING = "executing"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkflowStep:
    """Single step in a workflow."""
    id: str
    agent: str
    action: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    error: Optional[str] = None


@dataclass
class Workflow:
    """Complete workflow definition."""
    id: str
    name: str
    steps: List[WorkflowStep]
    state: WorkflowState
    metadata: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)


class Orchestrator(BaseAgent):
    """Main orchestrator agent that coordinates all other agents."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize orchestrator.
        
        Args:
            config: Orchestrator configuration
        """
        super().__init__(
            name="orchestrator",
            role=AgentRole.ORCHESTRATOR,
            config=config
        )
        
        self.agents: Dict[str, BaseAgent] = {}
        self.workflows: Dict[str, Workflow] = {}
        self.agent_registry: Dict[str, Dict[str, Any]] = {}
        self.execution_pool = None
        
        self._setup_capabilities()
        
    def _setup_capabilities(self):
        """Setup orchestrator capabilities."""
        self.add_capability(AgentCapability(
            name="register_agent",
            description="Register a new agent",
            input_types=["agent_definition"],
            output_types=["registration_result"]
        ))
        
        self.add_capability(AgentCapability(
            name="create_workflow",
            description="Create document processing workflow",
            input_types=["document_path", "pipeline_config"],
            output_types=["workflow_id"]
        ))
        
        self.add_capability(AgentCapability(
            name="execute_workflow",
            description="Execute a workflow",
            input_types=["workflow_id"],
            output_types=["workflow_results"]
        ))
        
        self.add_capability(AgentCapability(
            name="monitor_workflow",
            description="Monitor workflow execution",
            input_types=["workflow_id"],
            output_types=["workflow_status"]
        ))
        
    async def initialize(self) -> bool:
        """Initialize orchestrator and agent pool."""
        try:
            self.logger.info("Initializing orchestrator...")
            self.execution_pool = asyncio.Queue()
            self.update_status(AgentStatus.READY)
            
            # Load agent registry
            await self._load_agent_registry()
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize: {e}")
            self.update_status(AgentStatus.ERROR)
            return False
    
    async def shutdown(self) -> bool:
        """Shutdown orchestrator and all agents."""
        try:
            self.logger.info("Shutting down orchestrator...")
            
            # Shutdown all registered agents
            for agent_name, agent in self.agents.items():
                await agent.shutdown()
                
            self.update_status(AgentStatus.IDLE)
            return True
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            return False
    
    async def process(self, message: AgentMessage) -> AgentMessage:
        """Process orchestrator messages.
        
        Args:
            message: Incoming message
            
        Returns:
            Response message
        """
        self.update_status(AgentStatus.PROCESSING)
        
        try:
            if message.action == "register_agent":
                result = await self._register_agent(message.payload)
                
            elif message.action == "create_workflow":
                result = await self._create_workflow(message.payload)
                
            elif message.action == "execute_workflow":
                result = await self._execute_workflow(message.payload)
                
            elif message.action == "monitor_workflow":
                result = await self._monitor_workflow(message.payload)
                
            else:
                raise ValueError(f"Unknown action: {message.action}")
            
            self.update_status(AgentStatus.READY)
            
            return self.create_response(
                recipient=message.sender,
                action=f"{message.action}_response",
                payload=result,
                correlation_id=message.correlation_id
            )
            
        except Exception as e:
            self.logger.error(f"Processing error: {e}")
            self.update_status(AgentStatus.ERROR)
            
            return self.create_response(
                recipient=message.sender,
                action="error",
                payload={"error": str(e)},
                correlation_id=message.correlation_id
            )
    
    async def _register_agent(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new agent.
        
        Args:
            payload: Agent registration details
            
        Returns:
            Registration result
        """
        agent_name = payload.get("name")
        agent_class = payload.get("class")
        agent_config = payload.get("config", {})
        
        if agent_name in self.agents:
            return {"success": False, "error": "Agent already registered"}
        
        try:
            # Create agent instance
            agent = agent_class(config=agent_config)
            await agent.initialize()
            
            # Register agent
            self.agents[agent_name] = agent
            self.agent_registry[agent_name] = {
                "role": agent.role.value,
                "capabilities": [cap.name for cap in agent.capabilities],
                "status": agent.status.value
            }
            
            self.logger.info(f"Registered agent: {agent_name}")
            return {"success": True, "agent": agent_name}
            
        except Exception as e:
            self.logger.error(f"Failed to register agent {agent_name}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _create_workflow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new workflow.
        
        Args:
            payload: Workflow configuration
            
        Returns:
            Workflow creation result
        """
        document_path = payload.get("document_path")
        pipeline_config = payload.get("pipeline_config", {})
        
        # Generate workflow ID
        workflow_id = str(uuid.uuid4())
        
        # Analyze document and create workflow steps
        steps = await self._plan_workflow(document_path, pipeline_config)
        
        # Create workflow
        workflow = Workflow(
            id=workflow_id,
            name=f"Process {Path(document_path).name}",
            steps=steps,
            state=WorkflowState.PLANNING,
            metadata={
                "document_path": document_path,
                "pipeline_config": pipeline_config
            }
        )
        
        self.workflows[workflow_id] = workflow
        
        self.logger.info(f"Created workflow: {workflow_id}")
        return {
            "workflow_id": workflow_id,
            "steps": len(steps),
            "estimated_agents": list(set(step.agent for step in steps))
        }
    
    async def _plan_workflow(
        self,
        document_path: str,
        pipeline_config: Dict[str, Any]
    ) -> List[WorkflowStep]:
        """Plan workflow steps based on document and configuration.
        
        Args:
            document_path: Path to document
            pipeline_config: Pipeline configuration
            
        Returns:
            List of workflow steps
        """
        steps = []
        step_id = 0
        
        # Determine file type
        file_path = Path(document_path)
        file_extension = file_path.suffix.lower()
        
        # Step 1: Load document
        steps.append(WorkflowStep(
            id=f"step_{step_id}",
            agent="loader_agent",
            action="load_document",
            inputs={
                "path": document_path,
                "file_type": file_extension
            }
        ))
        step_id += 1
        
        # Step 2: Process based on file type
        if file_extension == ".pdf":
            processor = pipeline_config.get("pdf_processor", "enhanced_docling")
            steps.append(WorkflowStep(
                id=f"step_{step_id}",
                agent="pdf_processor_agent",
                action=f"process_{processor}",
                inputs={
                    "document": f"step_{step_id-1}.output",
                    "ocr_mode": pipeline_config.get("ocr_mode", "hybrid"),
                    "extract_tables": pipeline_config.get("extract_tables", True)
                },
                dependencies=[f"step_{step_id-1}"]
            ))
            
        elif file_extension in [".docx", ".doc"]:
            steps.append(WorkflowStep(
                id=f"step_{step_id}",
                agent="docx_processor_agent",
                action="process_mammoth",
                inputs={"document": f"step_{step_id-1}.output"},
                dependencies=[f"step_{step_id-1}"]
            ))
            
        elif file_extension in [".pptx", ".ppt"]:
            steps.append(WorkflowStep(
                id=f"step_{step_id}",
                agent="pptx_processor_agent",
                action="process_markitdown",
                inputs={"document": f"step_{step_id-1}.output"},
                dependencies=[f"step_{step_id-1}"]
            ))
        
        step_id += 1
        
        # Step 3: Transform based on pipeline type
        pipeline_type = pipeline_config.get("pipeline_type", "text")
        
        if pipeline_type == "markdown":
            steps.append(WorkflowStep(
                id=f"step_{step_id}",
                agent="transformer_agent",
                action="text_to_markdown",
                inputs={"text": f"step_{step_id-1}.output"},
                dependencies=[f"step_{step_id-1}"]
            ))
            
        elif pipeline_type == "json":
            steps.append(WorkflowStep(
                id=f"step_{step_id}",
                agent="transformer_agent",
                action="text_to_json",
                inputs={
                    "text": f"step_{step_id-1}.output",
                    "schema": pipeline_config.get("json_schema")
                },
                dependencies=[f"step_{step_id-1}"]
            ))
            
        elif pipeline_type == "weaviate":
            # Add chunking step
            steps.append(WorkflowStep(
                id=f"step_{step_id}",
                agent="transformer_agent",
                action="chunk_text",
                inputs={
                    "text": f"step_{step_id-1}.output",
                    "chunk_size": pipeline_config.get("chunk_size", 1000)
                },
                dependencies=[f"step_{step_id-1}"]
            ))
            step_id += 1
            
            # Add embedding step
            steps.append(WorkflowStep(
                id=f"step_{step_id}",
                agent="storage_agent",
                action="store_in_weaviate",
                inputs={
                    "chunks": f"step_{step_id-1}.output",
                    "collection": pipeline_config.get("collection", "Documents")
                },
                dependencies=[f"step_{step_id-1}"]
            ))
        
        return steps
    
    async def _execute_workflow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow.
        
        Args:
            payload: Execution parameters
            
        Returns:
            Execution results
        """
        workflow_id = payload.get("workflow_id")
        
        if workflow_id not in self.workflows:
            return {"success": False, "error": "Workflow not found"}
        
        workflow = self.workflows[workflow_id]
        workflow.state = WorkflowState.EXECUTING
        
        try:
            # Execute workflow steps
            for step in workflow.steps:
                if step.status == "completed":
                    continue
                
                # Check dependencies
                if not await self._check_dependencies(workflow, step):
                    continue
                
                # Execute step
                result = await self._execute_step(workflow, step)
                
                if not result["success"]:
                    workflow.state = WorkflowState.FAILED
                    return {
                        "success": False,
                        "workflow_id": workflow_id,
                        "error": result.get("error"),
                        "failed_step": step.id
                    }
            
            workflow.state = WorkflowState.COMPLETED
            
            return {
                "success": True,
                "workflow_id": workflow_id,
                "results": workflow.results
            }
            
        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}")
            workflow.state = WorkflowState.FAILED
            return {
                "success": False,
                "workflow_id": workflow_id,
                "error": str(e)
            }
    
    async def _execute_step(
        self,
        workflow: Workflow,
        step: WorkflowStep
    ) -> Dict[str, Any]:
        """Execute a single workflow step.
        
        Args:
            workflow: Workflow context
            step: Step to execute
            
        Returns:
            Execution result
        """
        try:
            # Get agent
            agent = self.agents.get(step.agent)
            if not agent:
                return {"success": False, "error": f"Agent {step.agent} not found"}
            
            # Prepare inputs
            inputs = await self._resolve_inputs(workflow, step.inputs)
            
            # Send message to agent
            message = AgentMessage(
                sender=self.name,
                recipient=step.agent,
                action=step.action,
                payload=inputs,
                correlation_id=workflow.id
            )
            
            # Process message
            response = await agent.process(message)
            
            # Store outputs
            step.outputs = response.payload
            step.status = "completed"
            
            # Store in workflow results
            workflow.results[step.id] = step.outputs
            
            return {"success": True, "outputs": step.outputs}
            
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            return {"success": False, "error": str(e)}
    
    async def _check_dependencies(
        self,
        workflow: Workflow,
        step: WorkflowStep
    ) -> bool:
        """Check if step dependencies are satisfied.
        
        Args:
            workflow: Workflow context
            step: Step to check
            
        Returns:
            True if dependencies are satisfied
        """
        for dep_id in step.dependencies:
            dep_step = next((s for s in workflow.steps if s.id == dep_id), None)
            if not dep_step or dep_step.status != "completed":
                return False
        return True
    
    async def _resolve_inputs(
        self,
        workflow: Workflow,
        inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve input references.
        
        Args:
            workflow: Workflow context
            inputs: Input dictionary with potential references
            
        Returns:
            Resolved inputs
        """
        resolved = {}
        
        for key, value in inputs.items():
            if isinstance(value, str) and value.startswith("step_"):
                # Resolve step output reference
                parts = value.split(".")
                if len(parts) == 2:
                    step_id, output_key = parts
                    if step_id in workflow.results:
                        resolved[key] = workflow.results[step_id].get(output_key)
                    else:
                        resolved[key] = None
                else:
                    resolved[key] = value
            else:
                resolved[key] = value
                
        return resolved
    
    async def _monitor_workflow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor workflow execution.
        
        Args:
            payload: Monitoring parameters
            
        Returns:
            Workflow status
        """
        workflow_id = payload.get("workflow_id")
        
        if workflow_id not in self.workflows:
            return {"success": False, "error": "Workflow not found"}
        
        workflow = self.workflows[workflow_id]
        
        # Gather step statuses
        step_statuses = []
        for step in workflow.steps:
            step_statuses.append({
                "id": step.id,
                "agent": step.agent,
                "action": step.action,
                "status": step.status,
                "error": step.error
            })
        
        return {
            "workflow_id": workflow_id,
            "state": workflow.state.value,
            "steps": step_statuses,
            "completed_steps": sum(1 for s in workflow.steps if s.status == "completed"),
            "total_steps": len(workflow.steps)
        }
    
    async def _load_agent_registry(self):
        """Load agent registry from configuration."""
        # This would load from a configuration file or database
        # For now, we'll use a basic registry
        self.agent_registry = {
            "loader_agent": {
                "role": "loader",
                "capabilities": ["load_document", "validate_format"]
            },
            "pdf_processor_agent": {
                "role": "processor",
                "capabilities": ["process_enhanced_docling", "process_pymupdf", "process_hybrid"]
            },
            "transformer_agent": {
                "role": "transformer",
                "capabilities": ["text_to_markdown", "text_to_json", "chunk_text"]
            },
            "storage_agent": {
                "role": "storage",
                "capabilities": ["store_in_weaviate", "retrieve_from_weaviate"]
            }
        }