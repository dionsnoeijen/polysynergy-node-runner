<div align="center">
  <img src="https://www.polysynergy.com/ps-color-logo-with-text.svg" alt="PolySynergy Logo" width="300">
</div>

# PolySynergy Node Runner

A Python framework for executing node-based workflows with support for AWS services, real-time messaging, and dynamic code generation.

## Overview

The PolySynergy Node Runner is a sophisticated workflow execution engine that enables the creation and execution of complex, interconnected node-based processes. It features dynamic code generation, state management, and integration with cloud services.

## Features

- **Node-Based Architecture**: Create workflows using interconnected nodes with inputs and outputs
- **Dynamic Code Generation**: Automatically generates executable Python code from node definitions
- **AWS Integration**: Built-in support for S3, DynamoDB, and Secrets Manager
- **State Management**: Comprehensive execution state tracking and persistence
- **Template System**: Jinja2-like placeholder replacement for dynamic values
- **Async Support**: Full asynchronous execution capabilities
- **Testing Framework**: Comprehensive test suite with unit and integration tests

## Architecture

The framework is organized into three main contexts:

### 1. Setup Context (`polysynergy_node_runner/setup_context/`)
Defines the structure and configuration of nodes:
- **Node**: Base class for all nodes with properties like id, handle, variables, and state
- **NodeVariable**: Represents configurable parameters for nodes
- **ServiceNode**: Special type of node for service-based operations
- **ConnectionManager**: Manages connections between nodes
- **VariableManager**: Handles node variable management
- **FileResolver**: Resolves file paths and imports

### 2. Execution Context (`polysynergy_node_runner/execution_context/`)
Handles runtime execution of node flows:
- **Flow**: Orchestrates node execution with traversal logic (forward/backward)
- **ExecutableNode**: Runtime representation of nodes during execution
- **Context**: Execution context containing environment and flow data
- **Connection**: Represents data flow between nodes
- **Mixins**: Modular behaviors for nodes (state lifecycle, traversal, resurrection, etc.)
- **Utils**: Helper functions for connections, serialization, and secret handling

### 3. Services (`polysynergy_node_runner/services/`)
Supporting services for the framework:
- **CodeGen**: Generates executable Python code from node definitions
- **SecretsManager**: AWS Secrets Manager integration
- **S3Service**: AWS S3 integration
- **ExecutionStorageService**: DynamoDB storage for execution state
- **ActiveListenersService**: Manages active event listeners

## Installation

### Prerequisites
- Python 3.12+
- Poetry (for dependency management)

### Setup
```bash
# Clone the repository
git clone <repository-url>
cd node_runner

# Install dependencies
poetry install

# Activate the virtual environment
poetry shell
```

## Usage

For examples of how to create and implement nodes, refer to the individual node repositories which contain the actual node implementations and serve as the definitive guide for node development.

## Configuration

### Environment Variables
- `AWS_REGION`: AWS region for services
- `REDIS_URL`: Redis connection URL

### AWS Services Setup
The framework requires appropriate AWS credentials and permissions for:
- **S3**: Object storage for files and artifacts
- **DynamoDB**: Execution state persistence
- **Secrets Manager**: Secure credential storage

## Testing

The project uses pytest with comprehensive test coverage:

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

# Run tests with verbose output
poetry run pytest -v

# Skip slow tests
poetry run pytest -m "not slow"

# Skip AWS-dependent tests
poetry run pytest -m "not aws"
```

### Test Markers
- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.slow`: Slow running tests
- `@pytest.mark.aws`: Tests requiring AWS services

## Key Concepts

### Nodes
Basic units of computation with inputs/outputs and execution logic. Each node can:
- Define variables for configuration
- Execute business logic
- Connect to other nodes
- Maintain execution state

### Connections
Define data flow between nodes, including "driving" connections that determine execution order.

### Flow Execution
Nodes execute based on connection states and traversal rules. The framework supports:
- Forward traversal (normal execution)
- Backward traversal (for cleanup/rollback)
- State resurrection (recovering from failures)

### State Management
Nodes have execution states:
- `pending`: Not yet executed
- `processed`: Successfully completed
- `killed`: Terminated due to error
- `skipped`: Bypassed during execution

### Placeholder System
Template replacement system using Jinja2-like syntax:
```python
# In node configuration
"message": "Hello {{ user.name }}, your order {{ order.id }} is ready!"

# Gets resolved at runtime to:
"message": "Hello John, your order 12345 is ready!"
```

## Code Generation

The framework can generate standalone executable Python scripts from node definitions:

```python
from polysynergy_node_runner.services.codegen.build_executable import build_executable

# Generate executable code
executable_code = build_executable(
    nodes=node_definitions,
    connections=connection_definitions,
    run_id="unique-run-id"
)

# The generated code can be executed independently
exec(executable_code)
```

## AWS Lambda Integration

The framework supports deployment as AWS Lambda functions with automatic scaling and event-driven execution.

## Development

### Package Management
```bash
# Add a new dependency
poetry add <package>

# Add a development dependency
poetry add --dev <package>

# Update dependencies
poetry update
```

### Code Quality
The project maintains high code quality through:
- Comprehensive test coverage
- Type hints where applicable
- Modular architecture with clear separation of concerns
- Extensive documentation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

[License information to be added]

## Support

For issues and questions:
- Check the test files for usage examples
- Review the CLAUDE.md file for development guidelines
- Create an issue in the repository

## Dependencies

### Core Dependencies
- **boto3**: AWS SDK for Python
- **redis**: Caching and state management
- **jinja2**: Template engine for placeholders

### Development Dependencies
- **pytest**: Testing framework
- **pytest-asyncio**: Async testing support
- **pytest-cov**: Coverage reporting
- **pytest-mock**: Mocking utilities

## Version

Current version: 0.1.0

This framework is under active development and the API may change between versions.