import pytest
from polysynergy_node_runner.services.codegen.steps.build_group_nodes_code import build_group_nodes_code


@pytest.mark.unit
class TestBuildGroupNodesCode:

    def test_generates_simple_group_node_without_paths(self):
        """Test that a GroupNode without path properties generates pass statement."""
        connections = [
            {
                "sourceNodeId": "node-1",
                "sourceHandle": "output",
                "targetNodeId": "group-1",
                "targetGroupId": "group-1",
                "targetHandle": "0"
            }
        ]
        groups_with_output = {"group-1"}

        result = build_group_nodes_code(connections, groups_with_output)

        assert "class GroupNode_group_1(ExecutableNode):" in result
        assert "a_output = None" in result
        assert "def execute(self):" in result
        assert "pass" in result

    def test_generates_group_node_with_true_path_killing_logic(self):
        """Test that GroupNode with true_path property generates killing logic."""
        connections = [
            {
                "sourceNodeId": "node-1",
                "sourceHandle": "true_path",
                "targetNodeId": "group-1",
                "targetGroupId": "group-1",
                "targetHandle": "0"
            }
        ]
        groups_with_output = {"group-1"}

        result = build_group_nodes_code(connections, groups_with_output)

        assert "a_true_path = None" in result
        # Check for mirroring logic
        assert "for in_conn in self.get_in_connections():" in result
        assert "if in_conn.is_killer():" in result
        assert "if self.a_true_path is False:" in result
        assert "connection.make_killer()" in result
        # Should not have pass when there's logic
        lines = result.split('\n')
        execute_lines = [l for l in lines if 'def execute' in l or (l.strip() and l.startswith('        '))]
        assert not any('pass' in l for l in execute_lines if l.strip())

    def test_generates_group_node_with_false_path_killing_logic(self):
        """Test that GroupNode with false_path property generates killing logics."""
        connections = [
            {
                "sourceNodeId": "node-1",
                "sourceHandle": "false_path",
                "targetNodeId": "group-1",
                "targetGroupId": "group-1",
                "targetHandle": "1"
            }
        ]
        groups_with_output = {"group-1"}

        result = build_group_nodes_code(connections, groups_with_output)

        assert "a_false_path = None" in result

        # Check for mirroring logic
        assert "for in_conn in self.get_in_connections():" in result
        assert "if in_conn.is_killer():" in result

        # Check for error case (false_path is truthy) - kills all except false_path
        assert "if self.a_false_path:" in result
        assert "for connection in [c for c in self.get_out_connections() if c.source_handle != 'a_false_path']:" in result

    def test_generates_group_node_with_both_true_and_false_paths(self):
        """Test that GroupNode with both true_path and false_path generates complete logic."""
        connections = [
            {
                "sourceNodeId": "node-1",
                "sourceHandle": "true_path",
                "targetNodeId": "group-1",
                "targetGroupId": "group-1",
                "targetHandle": "0"
            },
            {
                "sourceNodeId": "node-1",
                "sourceHandle": "false_path",
                "targetNodeId": "group-1",
                "targetGroupId": "group-1",
                "targetHandle": "1"
            }
        ]
        groups_with_output = {"group-1"}

        result = build_group_nodes_code(connections, groups_with_output)

        # Both properties should exist
        assert "a_true_path = None" in result
        assert "a_false_path = None" in result

        # Should have connection mirroring logic
        assert "for in_conn in self.get_in_connections():" in result
        assert "if in_conn.is_killer():" in result

        # Should have specific property checks
        assert "if self.a_true_path is False:" in result
        assert "if self.a_false_path:" in result

    def test_generates_group_node_with_multiple_source_nodes(self):
        """Test that GroupNode with multiple source nodes uses different prefixes."""
        connections = [
            {
                "sourceNodeId": "node-1",
                "sourceHandle": "true_path",
                "targetNodeId": "group-1",
                "targetGroupId": "group-1",
                "targetHandle": "0"
            },
            {
                "sourceNodeId": "node-2",
                "sourceHandle": "true_path",
                "targetNodeId": "group-1",
                "targetGroupId": "group-1",
                "targetHandle": "2"
            }
        ]
        groups_with_output = {"group-1"}

        result = build_group_nodes_code(connections, groups_with_output)

        # Should have both prefixed properties
        assert "a_true_path = None" in result
        assert "b_true_path = None" in result

        # Should have mirroring logic
        assert "for in_conn in self.get_in_connections():" in result

        # Both should have separate property checks
        assert "if self.a_true_path is False:" in result
        assert "if self.b_true_path is False:" in result

    def test_skips_group_without_output(self):
        """Test that groups not in groups_with_output are skipped."""
        connections = [
            {
                "sourceNodeId": "node-1",
                "sourceHandle": "output",
                "targetNodeId": "group-1",
                "targetGroupId": "group-1",
                "targetHandle": "0"
            }
        ]
        groups_with_output = set()  # Empty set

        result = build_group_nodes_code(connections, groups_with_output)

        assert result == ""

    def test_handles_empty_connections(self):
        """Test that empty connections list returns empty string."""
        connections = []
        groups_with_output = {"group-1"}

        result = build_group_nodes_code(connections, groups_with_output)

        assert result == ""

    def test_generates_multiple_group_nodes(self):
        """Test that multiple groups generate separate class definitions."""
        connections = [
            {
                "sourceNodeId": "node-1",
                "sourceHandle": "true_path",
                "targetNodeId": "group-1",
                "targetGroupId": "group-1",
                "targetHandle": "0"
            },
            {
                "sourceNodeId": "node-2",
                "sourceHandle": "false_path",
                "targetNodeId": "group-2",
                "targetGroupId": "group-2",
                "targetHandle": "0"
            }
        ]
        groups_with_output = {"group-1", "group-2"}

        result = build_group_nodes_code(connections, groups_with_output)

        assert "class GroupNode_group_1(ExecutableNode):" in result
        assert "class GroupNode_group_2(ExecutableNode):" in result
        assert "a_true_path = None" in result
        assert "a_false_path = None" in result
