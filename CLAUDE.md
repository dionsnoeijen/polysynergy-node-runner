# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development Setup
```bash
# Install dependencies using Poetry
poetry install

# Activate the virtual environment
poetry shell
```

### Testing
```bash
# Run all tests with coverage
poetry run pytest

# Run tests without coverage
poetry run pytest --no-cov

# Run only unit tests
poetry run pytest tests/unit -m unit

# Run only integration tests
poetry run pytest tests/integration -m integration

# Run a specific test file
poetry run pytest tests/unit/test_node.py

# Run a specific test method
poetry run pytest tests/unit/test_node.py::TestNode::test_node_initialization

# Run tests with verbose output
poetry run pytest -v

# Run tests and stop on first failure
poetry run pytest -x

# Skip slow tests
poetry run pytest -m "not slow"

# Skip AWS-dependent tests
poetry run pytest -m "not aws"
```

### Package Management
```bash
# Add a new dependency
poetry add <package>

# Add a development dependency
poetry add --dev <package>

# Update dependencies
poetry update
```

## Architecture Overview

This is the Polysynergy Node Runner, a Python framework for executing node-based workflows. The codebase is organized into three main contexts:

### 1. Setup Context (`polysynergy_node_runner/setup_context/`)
Defines the structure and configuration of nodes in the system:
- `Node`: Base class for all nodes with properties like id, handle, variables, and state
- `NodeVariable`: Represents configurable parameters for nodes
- `ServiceNode`: Special type of node for service-based operations
- `node_decorator.py`: Provides decorators for node registration

### 2. Execution Context (`polysynergy_node_runner/execution_context/`)
Handles the runtime execution of node flows:
- `Flow`: Orchestrates node execution with traversal logic (forward/backward)
- `ExecutableNode`: Runtime representation of nodes during execution
- `Context`: Execution context containing environment and flow data
- `Connection`: Represents data flow between nodes
- **Mixins**: Modular behaviors for nodes (state lifecycle, traversal, resurrection, etc.)
- **Utils**: Helper functions for connections, serialization, and secret handling

### 3. Services (`polysynergy_node_runner/services/`)
Supporting services for the framework:
- `codegen/`: Generates executable Python code from node definitions
  - Builds unified executable scripts with proper imports and initialization
  - Handles node groups and connection rewiring
- `secrets_manager.py`: AWS Secrets Manager integration
- `s3_service.py`: AWS S3 integration
- `execution_storage_service.py`: DynamoDB storage for execution state
- `active_listeners_service.py`: Manages active event listeners

## Key Concepts

- **Nodes**: Basic units of computation with inputs/outputs and execution logic
- **Connections**: Define data flow between nodes, including "driving" connections
- **Flow Execution**: Nodes execute based on connection states and traversal rules
- **State Management**: Nodes have execution states (pending, processed, killed, etc.)
- **Placeholder System**: Template replacement system using Jinja2-like syntax (`{{ variable }}`)

## Testing Structure

The project uses pytest with the following structure:
- `tests/unit/`: Unit tests for individual components
- `tests/integration/`: Integration tests for service interactions
- `tests/fixtures/`: Test data and fixtures
- `tests/conftest.py`: Shared pytest fixtures and configuration

Test markers:
- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.slow`: Slow running tests
- `@pytest.mark.aws`: Tests requiring AWS services

## External Dependencies

- AWS Services: S3, DynamoDB, Secrets Manager (via boto3)
- Redis: Caching and state management