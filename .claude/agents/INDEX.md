# Agent Registry

This registry defines the agent-driven architecture for the Professional Learning Plans project.

## Core Agents

### Analysis Agents
- **survey-analyst.md** - Analyzes survey data and feedback
- **data-validator.md** - Validates and cleans input data
- **theme-extractor.md** - Extracts themes from qualitative data

### Workflow Agents  
- **orchestrator.md** - Coordinates multi-step analysis workflows
- **project-manager.md** - Manages project setup and configuration

### Reporting Agents
- **report-generator.md** - Generates formatted reports and dashboards
- **stakeholder-communicator.md** - Creates stakeholder-specific outputs

## Usage Pattern

1. Projects are defined in `/projects/` with configuration
2. Agents are invoked through workflow scripts in `/workflows/`
3. Core modules provide reusable logic without API dependencies
4. All AI processing happens through Claude Code agents