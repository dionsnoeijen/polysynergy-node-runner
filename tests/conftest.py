import pytest
from unittest.mock import Mock, AsyncMock
from polysynergy_node_runner.execution_context.context import Context
from polysynergy_node_runner.execution_context.execution_state import ExecutionState
from polysynergy_node_runner.execution_context.flow import Flow
from polysynergy_node_runner.setup_context.node import Node


@pytest.fixture
def mock_context():
    """Mock context for testing."""
    context = Mock(spec=Context)
    context.environment = {}
    context.secrets = {}
    return context


@pytest.fixture
def mock_execution_state():
    """Mock execution state for testing."""
    return Mock(spec=ExecutionState)


@pytest.fixture
def mock_flow():
    """Mock flow for testing."""
    flow = Mock(spec=Flow)
    flow.execute_node = AsyncMock()
    flow.traverse_backward = AsyncMock()
    flow.traverse_forward = AsyncMock()
    return flow


@pytest.fixture
def sample_node():
    """Create a sample node for testing."""
    node = Node(
        id="test-node-1",
        context=Mock(spec=Context),
        state=Mock(spec=ExecutionState),
        flow=Mock(spec=Flow)
    )
    node.handle = "test_node"
    node.name = "Test Node"
    node.type = "test"
    return node


@pytest.fixture
def sample_template_values():
    """Sample values for template replacement testing."""
    return {
        "user": {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com"
        },
        "items": [
            {"name": "Item 1", "value": 100},
            {"name": "Item 2", "value": 200}
        ],
        "config": {
            "api_url": "https://api.example.com",
            "timeout": 30
        }
    }