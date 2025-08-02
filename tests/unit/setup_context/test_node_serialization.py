import pytest
from unittest.mock import Mock, patch

from polysynergy_node_runner.setup_context.node import Node
from polysynergy_node_runner.setup_context.node_variable import NodeVariable
from polysynergy_node_runner.execution_context.flow_state import FlowState


@pytest.mark.unit
class TestNodeSerialization:
    """Test Node.to_dict() serialization functionality"""
    
    def test_to_dict_minimal_node(self):
        """Test serialization of minimal node"""
        node = Node()
        
        with patch.object(node, '_get_icon_content') as mock_icon, \
             patch.object(node, '_get_documentation') as mock_docs, \
             patch.object(node, '_get_code') as mock_code:
            
            mock_icon.return_value = ""
            mock_docs.return_value = None
            mock_code.return_value = None
            
            result = node.to_dict()
            
            expected_keys = {
                "handle", "name", "path", "type", "icon", "category",
                "variables", "has_enabled_switch", "documentation", 
                "stateful", "default_flow_state", "version", "metadata", "code"
            }
            assert set(result.keys()) == expected_keys
            
            # Test default values
            assert result["handle"] is None
            assert result["name"] == ""
            assert result["path"] == ""
            assert result["type"] == ""
            assert result["icon"] == ""
            assert result["category"] == ""
            assert result["variables"] == []
            assert result["has_enabled_switch"] is True
            assert result["documentation"] is None
            assert result["stateful"] is True
            assert result["default_flow_state"] == FlowState.ENABLED.value
            assert result["version"] == 1.0
            assert result["metadata"] == {}
            assert result["code"] is None
    
    def test_to_dict_fully_configured_node(self):
        """Test serialization of fully configured node"""
        node = Node(id="test-node")
        
        # Set all configurable fields
        node.handle = "test_handle"
        node.name = "Test Node"
        node.path = "test.nodes.TestNode"
        node.type = "logic"
        node.icon = "test-icon.svg"
        node.category = "processing"
        node.has_play_button = True
        node.has_enabled_switch = False
        node.stateful = False
        node.flow_state = FlowState.PENDING
        node.version = 2.5
        node.metadata = {"custom": "data", "tags": ["test", "node"]}
        
        # Mock variables
        mock_var1 = Mock(spec=NodeVariable)
        mock_var1.to_dict.return_value = {"name": "var1", "type": "string"}
        mock_var2 = Mock(spec=NodeVariable)
        mock_var2.to_dict.return_value = {"name": "var2", "type": "number"}
        node.variables = [mock_var1, mock_var2]
        
        with patch.object(node, '_get_icon_content') as mock_icon, \
             patch.object(node, '_get_documentation') as mock_docs, \
             patch.object(node, '_get_code') as mock_code:
            
            mock_icon.return_value = "<svg>test icon</svg>"
            mock_docs.return_value = "# Test Documentation"
            mock_code.return_value = "def test_node(): pass"
            
            result = node.to_dict()
            
            # Test all values
            assert result["handle"] == "test_handle"
            assert result["name"] == "Test Node"
            assert result["path"] == "test.nodes.TestNode"
            assert result["type"] == "logic"
            assert result["icon"] == "<svg>test icon</svg>"
            assert result["category"] == "processing"
            assert result["has_play_button"] is True  # Should be included when True
            assert result["has_enabled_switch"] is False
            assert result["documentation"] == "# Test Documentation"
            assert result["stateful"] is False
            assert result["default_flow_state"] == FlowState.PENDING.value
            assert result["version"] == 2.5
            assert result["metadata"] == {"custom": "data", "tags": ["test", "node"]}
            assert result["code"] == "def test_node(): pass"
            
            # Test variables serialization
            assert len(result["variables"]) == 2
            assert {"name": "var1", "type": "string"} in result["variables"]
            assert {"name": "var2", "type": "number"} in result["variables"]
            
            # Verify method calls
            mock_var1.to_dict.assert_called_once()
            mock_var2.to_dict.assert_called_once()
    
    def test_to_dict_has_play_button_false(self):
        """Test that has_play_button is excluded when False"""
        node = Node()
        node.has_play_button = False
        
        with patch.object(node, '_get_icon_content') as mock_icon, \
             patch.object(node, '_get_documentation') as mock_docs, \
             patch.object(node, '_get_code') as mock_code:
            
            mock_icon.return_value = ""
            mock_docs.return_value = None
            mock_code.return_value = None
            
            result = node.to_dict()
            
            # has_play_button should not be in the result when False
            assert "has_play_button" not in result
    
    def test_to_dict_has_play_button_true(self):
        """Test that has_play_button is included when True"""
        node = Node()
        node.has_play_button = True
        
        with patch.object(node, '_get_icon_content') as mock_icon, \
             patch.object(node, '_get_documentation') as mock_docs, \
             patch.object(node, '_get_code') as mock_code:
            
            mock_icon.return_value = ""
            mock_docs.return_value = None
            mock_code.return_value = None
            
            result = node.to_dict()
            
            # has_play_button should be in the result when True
            assert result["has_play_button"] is True
    
    def test_to_dict_calls_file_methods(self):
        """Test that to_dict calls all file-related methods"""
        node = Node()
        
        with patch.object(node, '_get_icon_content') as mock_icon, \
             patch.object(node, '_get_documentation') as mock_docs, \
             patch.object(node, '_get_code') as mock_code:
            
            mock_icon.return_value = "icon content"
            mock_docs.return_value = "docs content"
            mock_code.return_value = "code content"
            
            result = node.to_dict()
            
            # Verify all file methods were called
            mock_icon.assert_called_once()
            mock_docs.assert_called_once()
            mock_code.assert_called_once()
            
            # Verify results are included
            assert result["icon"] == "icon content"
            assert result["documentation"] == "docs content"
            assert result["code"] == "code content"
    
    def test_to_dict_variables_exception_handling(self):
        """Test that to_dict handles variable serialization exceptions"""
        node = Node()
        
        # Create a mock variable that raises exception during to_dict
        mock_var = Mock(spec=NodeVariable)
        mock_var.to_dict.side_effect = Exception("Variable serialization error")
        node.variables = [mock_var]
        
        with patch.object(node, '_get_icon_content') as mock_icon, \
             patch.object(node, '_get_documentation') as mock_docs, \
             patch.object(node, '_get_code') as mock_code:
            
            mock_icon.return_value = ""
            mock_docs.return_value = None
            mock_code.return_value = None
            
            # This should raise an exception as the current implementation
            # doesn't handle variable serialization errors
            with pytest.raises(Exception, match="Variable serialization error"):
                node.to_dict()
    
    def test_to_dict_different_flow_states(self):
        """Test serialization with different flow states"""
        flow_states = [
            FlowState.ENABLED,
            FlowState.FLOW_IN,
            FlowState.FLOW_STOP,
            FlowState.PENDING
        ]
        
        for flow_state in flow_states:
            node = Node()
            node.flow_state = flow_state
            
            with patch.object(node, '_get_icon_content') as mock_icon, \
                 patch.object(node, '_get_documentation') as mock_docs, \
                 patch.object(node, '_get_code') as mock_code:
                
                mock_icon.return_value = ""
                mock_docs.return_value = None
                mock_code.return_value = None
                
                result = node.to_dict()
                
                assert result["default_flow_state"] == flow_state.value
    
    def test_to_dict_complex_metadata(self):
        """Test serialization with complex metadata"""
        node = Node()
        node.metadata = {
            "string_value": "test",
            "number_value": 42,
            "boolean_value": True,
            "list_value": [1, 2, 3],
            "dict_value": {"nested": "data"},
            "none_value": None
        }
        
        with patch.object(node, '_get_icon_content') as mock_icon, \
             patch.object(node, '_get_documentation') as mock_docs, \
             patch.object(node, '_get_code') as mock_code:
            
            mock_icon.return_value = ""
            mock_docs.return_value = None
            mock_code.return_value = None
            
            result = node.to_dict()
            
            # Metadata should be preserved as-is
            assert result["metadata"] == {
                "string_value": "test",
                "number_value": 42,
                "boolean_value": True,
                "list_value": [1, 2, 3],
                "dict_value": {"nested": "data"},
                "none_value": None
            }
    
    def test_to_dict_empty_variables_list(self):
        """Test serialization with empty variables list"""
        node = Node()
        node.variables = []
        
        with patch.object(node, '_get_icon_content') as mock_icon, \
             patch.object(node, '_get_documentation') as mock_docs, \
             patch.object(node, '_get_code') as mock_code:
            
            mock_icon.return_value = ""
            mock_docs.return_value = None
            mock_code.return_value = None
            
            result = node.to_dict()
            
            assert result["variables"] == []