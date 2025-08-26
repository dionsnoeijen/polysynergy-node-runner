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

## GroupNode Architecture

### Overview
GroupNodes are dynamically generated containers that allow multiple nodes to be treated as a single unit in the workflow. They enable visual organization and encapsulation of complex sub-flows while maintaining data flow connections to external nodes.

### GroupNode Generation Process

#### 1. Identification Phase
- `find_groups_with_output()` identifies which groups have outgoing connections
- Only groups with external output connections get generated as GroupNode classes
- Groups with no external connections are skipped (optimization)

#### 2. Code Generation Phase (`build_group_nodes_code.py`)
```python
# Generated GroupNode structure
class GroupNode_e6284949_e7ae_4349_aa36_dd28fe79ed93(ExecutableNode):
    a_instance = None  # from targetHandle storage
    b_knowledge = None  # from targetHandle knowledge
    
    def execute(self):
        pass
```

Properties are created with pattern: `{prefix}_{source_handle}` where:
- `prefix`: Alphabetic identifier (a, b, c...) for each internal source node
- `source_handle`: Original output handle from the internal node

#### 3. Connection Rewriting (`rewrite_connections_for_groups.py`)

**Phase 1 - Input Mapping**: Builds maps for connections going INTO groups
```python
group_prefix_map[group_id][source_node_id] = prefix  # Maps internal nodes to prefixes
group_target_map[group_id][target_handle] = new_handle  # Maps handles
```

**Phase 2 - Connection Modification**: Only rewrites connections FROM groups when:
- Source node exists in `group_prefix_map` (received inputs from outside)
- AND has `sourceGroupId`

**Critical Discovery**: Not all connections get rewritten! Service nodes inside groups that don't receive external inputs maintain their original `sourceNodeId`.

### Data Flow Architecture

#### 1. Simple Data Flow (Works Correctly)
```
StringNode (inside group) → GroupNode.a_output → ExternalNode
```

**Mechanism**:
1. `apply_from_incoming_connection()` is called on target node
2. `get_connection_source_variable()` resolves the data path:
   ```python
   source_node = get_node_by_id(connection.source_node_id)  # Gets GroupNode
   path_parts = connection.source_handle.split(".")         # ["a_output"]
   current = getattr(source_node, "a_output")               # Gets actual value
   ```
3. Data flows through GroupNode property as proxy

#### 2. Service Discovery Flow (Currently Broken)
```
SettingsNode (inside group) → GroupNode.a_instance → AgentNode.provide_instance()
```

**Problem**: 
- `find_connected_*` helpers expect nodes with `provide_instance()` method
- GroupNode lacks `provide_instance()` - it's only a data proxy
- Service interface is lost at the group boundary

### Service Discovery Challenge

#### Current Find Helper Pattern
```python
async def find_connected_storage(node: Node) -> Storage | None:
    storage_connections = [c for c in node.get_in_connections() if c.target_handle == "storage"]
    for conn in storage_connections:
        storage_node = node.state.get_node_by_id(conn.source_node_id)  # May get GroupNode
        if hasattr(storage_node, "provide_instance"):  # GroupNode fails this check
            return await storage_node.provide_instance()
```

#### Root Cause Analysis
1. **Data Flow**: Uses property proxy pattern - GroupNode acts as passthrough
2. **Service Discovery**: Requires method delegation - GroupNode has no `provide_instance()`
3. **Architecture Gap**: GroupNodes designed for data, not service interfaces

### Connection Data Structure

Connections contain crucial metadata for group traversal:
```python
{
    "id": "conn-1",
    "sourceNodeId": "actual-service-node-id",     # Original before rewriting
    "sourceGroupId": "group-1",                   # Container group
    "sourceHandle": "instance",                   # Original output handle  
    "targetNodeId": "external-node",
    "targetGroupId": None,
    "targetHandle": "storage"
}
```

**After rewriting (when applicable)**:
```python
{
    "sourceNodeId": "group-1",           # Changed to GroupNode
    "sourceHandle": "a_instance",        # Prefixed handle
    # ... other fields unchanged
}
```

### Future Enhancement Requirements

For proper service discovery through groups, one of these approaches is needed:

1. **GroupNode Service Delegation**: Make GroupNode implement service interfaces and delegate to internal nodes
2. **Smart Find Helpers**: Modify find helpers to traverse through GroupNodes to actual service providers  
3. **Connection Preservation**: Maintain direct service references even when grouped
4. **Hybrid Approach**: Different handling for data flow vs service discovery

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