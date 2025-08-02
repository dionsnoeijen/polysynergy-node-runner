import pytest
from unittest.mock import Mock, AsyncMock
from polysynergy_node_runner.execution_context.flow import Flow
from polysynergy_node_runner.execution_context.executable_node import ExecutableNode


@pytest.mark.unit
class TestFlow:
    
    def test_flow_creation(self):
        flow = Flow()
        assert flow is not None
    
    @pytest.mark.asyncio
    async def test_execute_node_blocking(self):
        flow = Flow()
        
        node = Mock(spec=ExecutableNode)
        node.is_blocking.return_value = True
        node.id = "test-node"
        node.handle = "test_handle"
        
        await flow.execute_node(node)
        
        node.is_blocking.assert_called_once()
        node.is_pending.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_execute_node_pending(self):
        flow = Flow()
        
        node = Mock(spec=ExecutableNode)
        node.is_blocking.return_value = False
        node.is_pending.return_value = True
        node.id = "test-node"
        node.handle = "test_handle"
        
        await flow.execute_node(node)
        
        node.is_blocking.assert_called_once()
        node.is_pending.assert_called_once()
        node.is_killed.assert_not_called()