import pytest
from unittest.mock import Mock
from polysynergy_node_runner.setup_context.node import Node
from polysynergy_node_runner.execution_context.context import Context
from polysynergy_node_runner.execution_context.execution_state import ExecutionState
from polysynergy_node_runner.execution_context.flow import Flow


@pytest.mark.unit
class TestNode:
    
    def test_node_initialization(self):
        context = Mock(spec=Context)
        state = Mock(spec=ExecutionState)
        flow = Mock(spec=Flow)
        
        node = Node(
            id="test-node-1",
            context=context,
            state=state,
            flow=flow
        )
        
        assert node.id == "test-node-1"
        assert node.context == context
        assert node.state == state
        assert node.flow == flow
        assert node.handle is None
        assert node.name == ""
        assert node.has_enabled_switch is True
        assert node.stateful is True
    
    def test_node_with_handle_and_name(self, sample_node):
        assert sample_node.handle == "test_node"
        assert sample_node.name == "Test Node"
        assert sample_node.type == "test"
    
    def test_get_in_connections_default(self, sample_node):
        connections = sample_node.get_in_connections()
        assert connections == []
    
    def test_get_out_connections_default(self, sample_node):
        connections = sample_node.get_out_connections()
        assert connections == []