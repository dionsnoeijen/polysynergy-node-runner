import pytest
import re
from polysynergy_node_runner.services.codegen.build_executable import generate_code_from_json
from tests.fixtures.codegen_samples import (
    SIMPLE_NODE_WORKFLOW,
    CONNECTED_NODES_WORKFLOW, 
    GROUP_WORKFLOW,
    COMPLEX_WORKFLOW,
    MOCK_WORKFLOW,
    EXPECTED_PATTERNS
)


@pytest.mark.integration
class TestCodegenIntegration:
    
    def test_generate_simple_node_workflow(self):
        """Test code generation for a simple single-node workflow."""
        result = generate_code_from_json(SIMPLE_NODE_WORKFLOW, "test-simple")
        
        # Check basic structure
        assert "#!/usr/bin/env python3" in result
        assert 'NODE_SETUP_VERSION_ID = "test-simple"' in result
        assert "def lambda_handler(event, context):" in result
        
        # Check node transformation (version format is V1_0, not _v1_0)
        assert "class TestNodeV1_0(ExecutableNode):" in result
        assert "@node" not in result  # Decorator should be stripped
        assert "def execute(self) -> Dict:" in result
        
        # Check imports were collected
        assert "import json" in result
        assert "from typing import Dict" in result
        
        # Check node instantiation (uses V1_0 format)
        assert "node_node_1 = TestNodeV1_0(" in result
        assert "id='node-1'" in result
        assert "handle='test_node'" in result
    
    def test_generate_connected_nodes_workflow(self):
        """Test code generation for nodes with connections."""
        result = generate_code_from_json(CONNECTED_NODES_WORKFLOW, "test-connected")
        
        # Check both nodes are generated
        assert "class InputNodeV1_0(ExecutableNode):" in result
        assert "class OutputNodeV1_0(ExecutableNode):" in result
        
        # Check connection is generated
        assert "connections.append(Connection(" in result
        assert "uuid='conn-1'" in result
        assert "source_node_id='input-node'" in result
        assert "target_node_id='output-node'" in result
        assert "source_handle='output'" in result
        assert "target_handle='data'" in result
        
        # Check mock condition for input category
        assert "if mock or 'input' != 'mock'" in result
    
    def test_generate_group_workflow(self):
        """Test code generation for workflows with group nodes."""
        result = generate_code_from_json(GROUP_WORKFLOW, "test-group")
        
        # Check that group with output is included
        assert "class ProcessorNodeV1_0(ExecutableNode):" in result
        assert "class ExternalNodeV1_0(ExecutableNode):" in result
        
        # Check group node creation
        assert "class GroupNode_group_1(ExecutableNode):" in result
        
        # Check connection from group is generated (since group has output)
        assert "connections.append(Connection(" in result
        assert "source_node_id='node-in-group'" in result
    
    def test_generate_complex_workflow(self):
        """Test code generation for complex workflow with versions and service nodes."""
        result = generate_code_from_json(COMPLEX_WORKFLOW, "test-complex")
        
        # Check version suffixes
        assert "class ApiClientV2_1(ExecutableNode):" in result
        assert "class DataTransformerV1_0(ExecutableNode):" in result
        
        # Check ServiceNode was converted to ExecutableNode
        assert "ServiceNode" not in result
        
        # Check imports from both nodes
        assert "import requests" in result
        assert "from typing import Optional" in result
        assert "from typing import Any, Dict" in result
        
        # Check flow state handling
        flow_state_pattern = r"node_transform_node\.flow_state = FlowState\.\w+"
        assert re.search(flow_state_pattern, result)
    
    def test_generate_mock_workflow(self):
        """Test code generation for workflows with mock nodes."""
        result = generate_code_from_json(MOCK_WORKFLOW, "test-mock")
        
        # Check mock condition handling
        assert "if mock or 'mock' != 'mock'" in result
        assert "if mock or 'logic' != 'mock'" in result
        
        # Both nodes should be generated
        assert "class MockInputV1_0(ExecutableNode):" in result
        assert "class RealProcessorV1_0(ExecutableNode):" in result
    
    def test_generated_code_structure(self):
        """Test that generated code has all expected structural elements."""
        result = generate_code_from_json(SIMPLE_NODE_WORKFLOW, "test-structure")
        
        # Check header patterns
        for pattern in EXPECTED_PATTERNS["header"]:
            assert pattern in result, f"Missing header pattern: {pattern}"
        
        # Check lambda handler patterns
        for pattern in EXPECTED_PATTERNS["lambda_handler"]:
            assert pattern in result, f"Missing lambda handler pattern: {pattern}"
        
        # Check execution environment patterns
        for pattern in EXPECTED_PATTERNS["execution_environment"]:
            assert pattern in result, f"Missing execution environment pattern: {pattern}"
    
    def test_empty_workflow(self):
        """Test code generation for empty workflow."""
        empty_workflow = {"nodes": [], "connections": []}
        
        result = generate_code_from_json(empty_workflow, "test-empty")
        
        # Should still generate basic structure
        assert "#!/usr/bin/env python3" in result
        assert "def lambda_handler(event, context):" in result
        assert 'NODE_SETUP_VERSION_ID = "test-empty"' in result
        
        # Should not have any node classes
        assert "class " not in result or "class GroupNode_" not in result
    
    def test_workflow_with_missing_fields(self):
        """Test code generation handles missing optional fields gracefully."""
        minimal_workflow = {
            "nodes": [
                {
                    "id": "minimal-node",
                    "handle": "minimal",
                    "code": "class Minimal(Node): pass"
                    # Missing: path, type, category, version, etc.
                }
            ],
            "connections": []
        }
        
        result = generate_code_from_json(minimal_workflow, "test-minimal")
        
        # Should still generate code without errors
        assert "class Minimal(ExecutableNode):" in result
        assert "node_minimal_node = Minimal(" in result
        assert "id='minimal-node'" in result
        assert "handle='minimal'" in result
    
    def test_node_variable_settings_import_filtering(self):
        """Test that node_variable_settings imports are properly filtered out."""
        workflow_with_filtered_import = {
            "nodes": [
                {
                    "id": "test-node",
                    "handle": "test",
                    "code": '''from polysynergy_node_runner.node_variable_settings import NodeVariable
import polysynergy_node_runner.node_variable_settings
from other_module import something

class TestNode(Node):
    pass'''
                }
            ],
            "connections": []
        }
        
        result = generate_code_from_json(workflow_with_filtered_import, "test-filter")
        
        # Filtered imports should not appear in final code
        assert "node_variable_settings" not in result
        
        # Other imports should be preserved
        assert "from other_module import something" in result
    
    @pytest.mark.slow
    def test_large_workflow_performance(self):
        """Test code generation performance with larger workflows."""
        # Create a workflow with many nodes and connections
        large_workflow = {
            "nodes": [
                {
                    "id": f"node-{i}",
                    "handle": f"node_{i}",
                    "path": f"test.nodes.Node{i}",
                    "code": f"@node()\nclass Node{i}(Node):\n    def execute(self): return {{'id': {i}}}"
                }
                for i in range(50)  # 50 nodes
            ],
            "connections": [
                {
                    "id": f"conn-{i}",
                    "sourceNodeId": f"node-{i}",
                    "sourceHandle": "output",
                    "targetNodeId": f"node-{i+1}",
                    "targetHandle": "input"
                }
                for i in range(49)  # 49 connections
            ]
        }
        
        result = generate_code_from_json(large_workflow, "test-large")
        
        # Should generate all nodes
        assert result.count("class Node") == 50
        assert result.count("connections.append(Connection(") == 49
        
        # Should not take excessively long (this is more of a smoke test)
        assert len(result) > 1000  # Should generate substantial code