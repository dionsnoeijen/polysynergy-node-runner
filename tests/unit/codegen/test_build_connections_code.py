import pytest
from polysynergy_node_runner.services.codegen.steps.build_connections_code import build_connections_code


@pytest.mark.unit 
class TestBuildConnectionsCode:
    
    def test_builds_simple_connection(self):
        connections = [
            {
                "id": "conn-1",
                "sourceNodeId": "node-1",
                "sourceHandle": "output",
                "targetNodeId": "node-2", 
                "targetHandle": "input"
            }
        ]
        nodes = [
            {"id": "node-1", "category": "logic"},
            {"id": "node-2", "category": "logic"}
        ]
        groups_with_output = set()
        
        result = build_connections_code(connections, nodes, groups_with_output)
        
        expected = (
            "        if mock or 'logic' != 'mock': connections.append(Connection(uuid='conn-1', "
            "source_node_id='node-1', source_handle='output', "
            "target_node_id='node-2', target_handle='input', context=connection_context))"
        )
        assert result == expected
    
    def test_builds_multiple_connections(self):
        connections = [
            {
                "id": "conn-1",
                "sourceNodeId": "node-1",
                "sourceHandle": "output",
                "targetNodeId": "node-2",
                "targetHandle": "input"
            },
            {
                "id": "conn-2", 
                "sourceNodeId": "node-2",
                "sourceHandle": "result",
                "targetNodeId": "node-3",
                "targetHandle": "data"
            }
        ]
        nodes = [
            {"id": "node-1", "category": "input"},
            {"id": "node-2", "category": "logic"},
            {"id": "node-3", "category": "output"}
        ]
        groups_with_output = set()
        
        result = build_connections_code(connections, nodes, groups_with_output)
        
        lines = result.split('\n')
        assert len(lines) == 2
        assert "connections.append(Connection(uuid='conn-1'" in lines[0]
        assert "connections.append(Connection(uuid='conn-2'" in lines[1]
        assert "if mock or 'input' != 'mock'" in lines[0]
        assert "if mock or 'logic' != 'mock'" in lines[1]
    
    def test_skips_self_referencing_group_connections(self):
        connections = [
            {
                "id": "conn-1",
                "sourceNodeId": "group-1",
                "sourceGroupId": "group-1",
                "targetNodeId": "node-2",
                "targetHandle": "input",
                "isInGroup": "group-1"
            }
        ]
        nodes = [
            {"id": "group-1", "category": "group"},
            {"id": "node-2", "category": "logic"}
        ]
        groups_with_output = set()
        
        result = build_connections_code(connections, nodes, groups_with_output)
        
        assert result == ""
    
    def test_skips_group_without_output(self):
        connections = [
            {
                "id": "conn-1",
                "sourceNodeId": "node-in-group",
                "sourceHandle": "output",
                "targetNodeId": "node-2",
                "targetHandle": "input"
            }
        ]
        nodes = [
            {"id": "node-in-group", "category": "group"},
            {"id": "node-2", "category": "logic"}
        ]
        groups_with_output = set()  # Empty set - no groups have output
        
        result = build_connections_code(connections, nodes, groups_with_output)
        
        assert result == ""
    
    def test_includes_group_with_output(self):
        connections = [
            {
                "id": "conn-1",
                "sourceNodeId": "node-in-group",
                "sourceHandle": "output", 
                "targetNodeId": "node-2",
                "targetHandle": "input"
            }
        ]
        nodes = [
            {"id": "node-in-group", "category": "group"},
            {"id": "node-2", "category": "logic"}
        ]
        groups_with_output = {"node-in-group"}  # This group has output
        
        result = build_connections_code(connections, nodes, groups_with_output)
        
        expected = (
            "        if mock or 'group' != 'mock': connections.append(Connection(uuid='conn-1', "
            "source_node_id='node-in-group', source_handle='output', "
            "target_node_id='node-2', target_handle='input', context=connection_context))"
        )
        assert result == expected
    
    def test_handles_mock_category_condition(self):
        connections = [
            {
                "id": "conn-1",
                "sourceNodeId": "node-1",
                "sourceHandle": "output",
                "targetNodeId": "node-2", 
                "targetHandle": "input"
            }
        ]
        nodes = [
            {"id": "node-1", "category": "mock"},  # Mock category
            {"id": "node-2", "category": "logic"}
        ]
        groups_with_output = set()
        
        result = build_connections_code(connections, nodes, groups_with_output)
        
        # Should generate condition that evaluates to: mock or 'mock' != 'mock' 
        # which simplifies to: mock or False, meaning only runs in mock mode
        assert "if mock or 'mock' != 'mock'" in result
        assert "connections.append(Connection(uuid='conn-1'" in result
    
    def test_handles_missing_node_category(self):
        connections = [
            {
                "id": "conn-1",
                "sourceNodeId": "node-1",
                "sourceHandle": "output",
                "targetNodeId": "node-2",
                "targetHandle": "input"
            }
        ]
        nodes = [
            {"id": "node-1"},  # No category field
            {"id": "node-2", "category": "logic"}
        ]
        groups_with_output = set()
        
        result = build_connections_code(connections, nodes, groups_with_output)
        
        # Should default to empty string for category
        assert "if mock or '' != 'mock'" in result
    
    def test_handles_missing_source_node(self):
        connections = [
            {
                "id": "conn-1", 
                "sourceNodeId": "nonexistent-node",
                "sourceHandle": "output",
                "targetNodeId": "node-2",
                "targetHandle": "input"
            }
        ]
        nodes = [
            {"id": "node-2", "category": "logic"}
        ]
        groups_with_output = set()
        
        result = build_connections_code(connections, nodes, groups_with_output)
        
        # Should handle missing node gracefully
        assert "if mock or '' != 'mock'" in result
        assert "connections.append(Connection(uuid='conn-1'" in result
    
    def test_handles_empty_inputs(self):
        assert build_connections_code([], [], set()) == ""
        assert build_connections_code([], [{"id": "node-1"}], set()) == ""