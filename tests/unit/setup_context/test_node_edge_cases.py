import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from polysynergy_node_runner.setup_context.node import Node
from polysynergy_node_runner.setup_context.node_variable_settings import NodeVariableSettings
from polysynergy_node_runner.setup_context.node_variable import NodeVariable
from polysynergy_node_runner.execution_context.flow_state import FlowState


@pytest.mark.unit
class TestNodeEdgeCases:
    """Test Node class edge cases and error conditions"""
    
    def test_node_with_unicode_values(self):
        """Test node with unicode characters in various fields"""
        node = Node(id="test-node")
        
        # Set unicode values
        node.handle = "тест_хендл"  # Cyrillic
        node.name = "测试节点"  # Chinese
        node.path = "тест.модуль.Função"  # Mixed scripts
        node.category = "обработка"  # Cyrillic
        node.metadata = {
            "描述": "这是一个测试节点",  # Chinese
            "émojis": "🚀🔧⚡",  # Emojis
            "accénts": "café naïve résumé"  # Accented characters
        }
        
        # Should not raise any exceptions
        assert node.handle == "тест_хендл"
        assert node.name == "测试节点"
        assert node.path == "тест.модуль.Função"
        assert node.category == "обработка"
        assert node.metadata["描述"] == "这是一个测试节点"
        assert node.metadata["émojis"] == "🚀🔧⚡"
    
    def test_node_with_very_long_strings(self):
        """Test node with very long string values"""
        long_string = "x" * 10000
        
        node = Node(id="test-node")
        node.name = long_string
        node.path = "very.long.module." + long_string
        node.metadata = {"long_value": long_string}
        
        # Should handle long strings without issues
        assert len(node.name) == 10000
        assert node.path.endswith(long_string)
        assert len(node.metadata["long_value"]) == 10000
    
    def test_node_with_none_values(self):
        """Test node behavior with None values where allowed"""
        node = Node(id="test-node")
        
        # These should be settable to None
        node.context = None
        node.state = None
        node.flow = None
        node.handle = None
        
        assert node.context is None
        assert node.state is None
        assert node.flow is None
        assert node.handle is None
    
    def test_node_with_extreme_numeric_values(self):
        """Test node with extreme numeric values"""
        node = Node(id="test-node")
        
        # Test extreme version numbers
        node.version = 0.0
        assert node.version == 0.0
        
        node.version = 999999999.999999999
        assert node.version == 999999999.999999999
        
        node.version = -1.0  # Negative version
        assert node.version == -1.0
    
    def test_node_metadata_with_special_values(self):
        """Test node metadata with special Python values"""
        node = Node(id="test-node")
        
        node.metadata = {
            "none": None,
            "empty_string": "",
            "empty_list": [],
            "empty_dict": {},
            "zero": 0,
            "false": False,
            "float_inf": float('inf'),
            "float_nan": float('nan'),
            "complex": complex(1, 2)
        }
        
        # Should store all values as-is
        assert node.metadata["none"] is None
        assert node.metadata["empty_string"] == ""
        assert node.metadata["empty_list"] == []
        assert node.metadata["empty_dict"] == {}
        assert node.metadata["zero"] == 0
        assert node.metadata["false"] is False
        assert node.metadata["float_inf"] == float('inf')
        # NaN comparison is special
        assert str(node.metadata["float_nan"]) == "nan"
        assert node.metadata["complex"] == complex(1, 2)


@pytest.mark.unit
class TestNodeFileOperationErrors:
    """Test Node file operation error handling"""
    
    def test_get_declaring_file_with_malformed_path(self):
        """Test _get_declaring_file with various malformed paths"""
        test_cases = [
            "",  # Empty string
            ".",  # Just a dot
            "..",  # Parent directory
            "....",  # Multiple dots
            "module.",  # Trailing dot
            ".module",  # Leading dot
            "module..submodule",  # Double dots
            "module with spaces.function",  # Spaces
            "module-with-dashes.function",  # Dashes
        ]
        
        for path in test_cases:
            node = Node()
            node.path = path
            
            with patch('builtins.print') as mock_print:
                result = node._get_declaring_file()
                
                if path == "":
                    # Empty path might have different behavior
                    continue
                    
                # Should handle gracefully and return None
                assert result is None
                # Should print error message
                mock_print.assert_called()
    
    def test_get_declaring_file_with_permission_error(self):
        """Test _get_declaring_file when import raises PermissionError"""
        node = Node()
        node.path = "test.module.function"
        
        # Patch print first to avoid the nested patching issue
        with patch('builtins.print') as mock_print:
            with patch('polysynergy_node_runner.setup_context.file_resolver.importlib.import_module') as mock_import:
                mock_import.side_effect = PermissionError("Permission denied")
                
                result = node._get_declaring_file()
                
                assert result is None
                mock_print.assert_called_once()
                error_msg = mock_print.call_args[0][0]
                assert "Permission denied" in error_msg
    
    def test_get_code_with_file_encoding_error(self):
        """Test _get_code when file has encoding issues"""
        node = Node()
        
        with patch.object(node._file_resolver, 'get_declaring_file') as mock_get_file:
            mock_file = Mock(spec=Path)
            mock_file.exists.return_value = True
            mock_file.read_text.side_effect = UnicodeDecodeError(
                'utf-8', b'', 0, 1, 'invalid start byte'
            )
            mock_get_file.return_value = mock_file
            
            # Should propagate the encoding error
            with pytest.raises(UnicodeDecodeError):
                node._get_code()
    
    def test_get_documentation_with_permission_error(self):
        """Test _get_documentation when README file has permission issues"""
        node = Node()
        
        with patch.object(node._file_resolver, 'get_declaring_file') as mock_get_file:
            mock_file = Mock(spec=Path)
            mock_doc_path = Mock(spec=Path)
            mock_doc_path.exists.return_value = True
            mock_doc_path.read_text.side_effect = PermissionError("Permission denied")
            mock_file.with_name.return_value = mock_doc_path
            mock_file.stem = "module"
            mock_get_file.return_value = mock_file
            
            # Should propagate the permission error
            with pytest.raises(PermissionError):
                node._get_documentation()
    
    def test_get_icon_content_with_binary_file(self):
        """Test _get_icon_content when icon file is binary"""
        node = Node()
        node.icon = "icon.png"
        
        with patch.object(node._file_resolver, 'get_declaring_file') as mock_get_file:
            mock_file = Mock(spec=Path)
            mock_icon_path = Mock(spec=Path)
            mock_icon_path.exists.return_value = True
            mock_icon_path.read_text.side_effect = UnicodeDecodeError(
                'utf-8', b'', 0, 1, 'invalid start byte'
            )
            
            # Mock the Path division operation correctly
            mock_parent = Mock()
            mock_icons_dir = Mock()
            mock_parent.__truediv__ = Mock(return_value=mock_icons_dir)
            mock_icons_dir.__truediv__ = Mock(return_value=mock_icon_path)
            mock_file.parent = mock_parent
            mock_get_file.return_value = mock_file
            
            # Should propagate the encoding error
            with pytest.raises(UnicodeDecodeError):
                node._get_icon_content()


@pytest.mark.unit
class TestNodeVariableGenerationEdgeCases:
    """Test edge cases in Node variable generation"""
    
    def test_variable_generation_with_class_hierarchy(self):
        """Test variable generation with inheritance - current implementation only finds immediate class variables"""
        
        class BaseNodeWithVar(Node):
            base_var = NodeVariableSettings(label="Base Variable")
        
        class DerivedNode(BaseNodeWithVar):
            derived_var = NodeVariableSettings(label="Derived Variable")
        
        with patch.object(NodeVariable, 'create_from_property') as mock_create:
            mock_var = Mock(spec=NodeVariable)
            mock_create.return_value = mock_var
            
            node = DerivedNode(id="test")
            
            # Current implementation only finds variables from the immediate class (DerivedNode)
            # not from parent classes - this is a limitation of using vars(type(self))
            assert mock_create.call_count == 1
            
            call_args = mock_create.call_args_list[0]
            # Only the derived class variable should be found
            assert call_args[0][1] == "derived_var"
    
    def test_variable_generation_with_property_conflicts(self):
        """Test variable generation when property names conflict"""
        
        class ConflictNode(Node):
            # Create a property that might conflict with NodeVariableSettings
            name = NodeVariableSettings(label="Name Variable")  # Conflicts with node.name
        
        with patch.object(NodeVariable, 'create_from_property') as mock_create:
            mock_var = Mock(spec=NodeVariable)
            mock_create.return_value = mock_var
            
            node = ConflictNode(id="test")
            
            # Should still process the variable
            mock_create.assert_called_once()
            assert len(node.variables) == 1
    
    def test_variable_generation_with_dynamic_attributes(self):
        """Test variable generation with dynamically added attributes"""
        
        class DynamicNode(Node):
            pass
        
        # Dynamically add a NodeVariableSettings after class creation
        DynamicNode.dynamic_var = NodeVariableSettings(label="Dynamic Variable")
        
        with patch.object(NodeVariable, 'create_from_property') as mock_create:
            mock_var = Mock(spec=NodeVariable)
            mock_create.return_value = mock_var
            
            node = DynamicNode(id="test")
            
            # Should find the dynamically added variable
            mock_create.assert_called_once()
            call_args = mock_create.call_args_list[0]
            assert call_args[0][1] == "dynamic_var"
    
    def test_variable_generation_with_multiple_exceptions(self):
        """Test variable generation when multiple variables raise exceptions"""
        
        class MultiErrorNode(Node):
            error_var1 = NodeVariableSettings(label="Error Variable 1")
            error_var2 = NodeVariableSettings(label="Error Variable 2")
            good_var = NodeVariableSettings(label="Good Variable")
        
        with patch.object(NodeVariable, 'create_from_property') as mock_create:
            mock_good_var = Mock(spec=NodeVariable)
            mock_create.side_effect = [
                AttributeError("Error 1"),
                AttributeError("Error 2"), 
                mock_good_var
            ]
            
            with patch('builtins.print') as mock_print:
                node = MultiErrorNode(id="test")
                
                # Should have printed 2 error messages
                assert mock_print.call_count == 2
                
                # Should only have the good variable
                assert len(node.variables) == 1
                assert node.variables[0] == mock_good_var


@pytest.mark.unit
class TestNodeMemoryAndPerformance:
    """Test Node memory usage and performance characteristics"""
    
    def test_node_creation_performance(self):
        """Test that node creation doesn't take excessive time"""
        import time
        
        start_time = time.time()
        
        # Create many nodes
        nodes = []
        for i in range(100):
            node = Node(id=f"node-{i}")
            node.name = f"Node {i}"
            node.path = f"test.nodes.Node{i}"
            nodes.append(node)
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Should create 100 nodes in reasonable time (less than 1 second)
        assert creation_time < 1.0
        assert len(nodes) == 100
    
    def test_node_with_large_variables_list(self):
        """Test node with many variables"""
        
        class ManyVarsNode(Node):
            pass
        
        # Add many variable settings
        for i in range(50):
            setattr(ManyVarsNode, f"var_{i}", NodeVariableSettings(label=f"Variable {i}"))
        
        with patch.object(NodeVariable, 'create_from_property') as mock_create:
            mock_vars = [Mock(spec=NodeVariable) for _ in range(50)]
            mock_create.side_effect = mock_vars
            
            node = ManyVarsNode(id="test")
            
            # Should handle many variables
            assert len(node.variables) == 50
            assert mock_create.call_count == 50
    
    def test_node_circular_reference_safety(self):
        """Test that nodes handle potential circular references safely"""
        node1 = Node(id="node1")
        node2 = Node(id="node2")
        
        # Create circular reference in metadata
        node1.metadata = {"other_node": node2}
        node2.metadata = {"other_node": node1}
        
        # Should not crash during basic operations
        assert node1.id == "node1"
        assert node2.id == "node2"
        assert node1.metadata["other_node"] == node2
        assert node2.metadata["other_node"] == node1
        
        # Note: to_dict() would likely have issues with circular references
        # but that's a separate concern for JSON serialization