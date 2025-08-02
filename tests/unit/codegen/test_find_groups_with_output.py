import pytest
from polysynergy_node_runner.services.codegen.steps.find_groups_with_output import find_groups_with_output


@pytest.mark.unit
class TestFindGroupsWithOutput:
    
    def test_identifies_group_with_external_output(self):
        connections = [
            {
                "sourceGroupId": "group-1",
                "sourceNodeId": "node-1",
                "targetGroupId": "group-2", 
                "targetNodeId": "node-2"
            }
        ]
        
        result = find_groups_with_output(connections)
        
        assert result == {"group-1"}
    
    def test_identifies_group_with_no_target_group(self):
        connections = [
            {
                "sourceGroupId": "group-1",
                "sourceNodeId": "node-1",
                "targetGroupId": None,
                "targetNodeId": "node-2"
            }
        ]
        
        result = find_groups_with_output(connections)
        
        assert result == {"group-1"}
    
    def test_excludes_internal_group_connections(self):
        # Connection within the same group should not count as output
        connections = [
            {
                "sourceGroupId": "group-1",
                "sourceNodeId": "node-1",
                "targetGroupId": "group-1",
                "targetNodeId": "node-2"
            }
        ]
        
        result = find_groups_with_output(connections)
        
        assert result == set()
    
    def test_excludes_dummy_group_connections(self):
        # When sourceNodeId equals sourceGroupId, it's a dummy connection
        connections = [
            {
                "sourceGroupId": "group-1",
                "sourceNodeId": "group-1",  # Same as group ID
                "targetGroupId": "group-2",
                "targetNodeId": "node-2"
            }
        ]
        
        result = find_groups_with_output(connections)
        
        assert result == set()
    
    def test_handles_multiple_groups_with_output(self):
        connections = [
            {
                "sourceGroupId": "group-1",
                "sourceNodeId": "node-1",
                "targetGroupId": "group-2",
                "targetNodeId": "node-2"
            },
            {
                "sourceGroupId": "group-2",
                "sourceNodeId": "node-3",
                "targetGroupId": "group-3",
                "targetNodeId": "node-4"
            },
            {
                "sourceGroupId": "group-3",
                "sourceNodeId": "node-5",
                "targetGroupId": None,
                "targetNodeId": "node-6"
            }
        ]
        
        result = find_groups_with_output(connections)
        
        assert result == {"group-1", "group-2", "group-3"}
    
    def test_handles_mixed_scenarios(self):
        connections = [
            # Group 1 has external output
            {
                "sourceGroupId": "group-1",
                "sourceNodeId": "node-1",
                "targetGroupId": "group-2",
                "targetNodeId": "node-2"
            },
            # Group 2 has internal connection (should not count)
            {
                "sourceGroupId": "group-2",
                "sourceNodeId": "node-3",
                "targetGroupId": "group-2",
                "targetNodeId": "node-4"
            },
            # Group 3 has dummy connection (should not count)
            {
                "sourceGroupId": "group-3",
                "sourceNodeId": "group-3",
                "targetGroupId": "group-1",
                "targetNodeId": "node-5"
            },
            # No group information
            {
                "sourceGroupId": None,
                "sourceNodeId": "node-6",
                "targetGroupId": None,
                "targetNodeId": "node-7"
            }
        ]
        
        result = find_groups_with_output(connections)
        
        assert result == {"group-1"}
    
    def test_handles_empty_connections(self):
        connections = []
        
        result = find_groups_with_output(connections)
        
        assert result == set()
    
    def test_handles_connections_without_groups(self):
        connections = [
            {
                "sourceGroupId": None,
                "sourceNodeId": "node-1",
                "targetGroupId": None,
                "targetNodeId": "node-2"
            }
        ]
        
        result = find_groups_with_output(connections)
        
        assert result == set()
    
    def test_handles_missing_keys(self):
        # Test with connections that might be missing some keys
        connections = [
            {
                "sourceNodeId": "node-1",
                "targetNodeId": "node-2"
                # Missing group IDs - .get() returns None
            },
            {
                "sourceGroupId": "group-1",
                "sourceNodeId": "node-3"
                # Missing target group ID - .get() returns None
                # This should add group-1 to output since sourceGroup != targetGroup (None)
                # and sourceNode != sourceGroup
            }
        ]
        
        result = find_groups_with_output(connections)
        
        # The second connection should match: group-1 != None and node-3 != group-1
        assert result == {"group-1"}