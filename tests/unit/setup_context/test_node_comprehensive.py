import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from polysynergy_node_runner.setup_context.node import Node
from polysynergy_node_runner.setup_context.node_variable import NodeVariable
from polysynergy_node_runner.setup_context.node_variable_settings import NodeVariableSettings
from polysynergy_node_runner.execution_context.context import Context
from polysynergy_node_runner.execution_context.execution_state import ExecutionState
from polysynergy_node_runner.execution_context.flow import Flow
from polysynergy_node_runner.execution_context.flow_state import FlowState


@pytest.mark.unit
class TestNodeInitialization:
    """Test Node class initialization and basic properties"""
    
    def test_minimal_node_creation(self):
        """Test creating a node with minimal parameters"""
        node = Node()
        
        # Test default values
        assert node.id == ''
        assert node.context is None
        assert node.state is None
        assert node.flow is None
        assert node.handle is None
        assert node.name == ''
        assert node.path == ''
        assert node.type == ''
        assert node.icon == ''
        assert node.category == ''
        assert node.has_play_button is False
        assert node.has_enabled_switch is True
        assert node.stateful is True
        assert node.flow_state == FlowState.ENABLED
        assert node.version == 1.0
        assert node.metadata == {}
        assert isinstance(node.variables, list)
    
    def test_node_creation_with_parameters(self):
        """Test creating a node with all init parameters"""
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
    
    def test_node_field_assignments(self):
        """Test that init=False fields can be assigned after creation"""
        node = Node(id="test-node")
        
        # Test field assignments
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
        node.metadata = {"custom": "data"}
        
        # Verify assignments
        assert node.handle == "test_handle"
        assert node.name == "Test Node"
        assert node.path == "test.nodes.TestNode"
        assert node.type == "logic"
        assert node.icon == "test-icon.svg"
        assert node.category == "processing"
        assert node.has_play_button is True
        assert node.has_enabled_switch is False
        assert node.stateful is False
        assert node.flow_state == FlowState.PENDING
        assert node.version == 2.5
        assert node.metadata == {"custom": "data"}


@pytest.mark.unit
class TestNodeConnectionMethods:
    """Test Node connection-related methods"""
    
    def test_get_in_connections_default(self):
        """Test default behavior of get_in_connections"""
        node = Node()
        result = node.get_in_connections()
        assert result == []
    
    def test_get_out_connections_default(self):
        """Test default behavior of get_out_connections"""
        node = Node()
        result = node.get_out_connections()
        assert result == []
    
    def test_get_driving_connections_default(self):
        """Test default behavior of get_driving_connections"""
        node = Node()
        result = node.get_driving_connections()
        assert result == []


@pytest.mark.unit
class TestNodeLoopMethods:
    """Test Node loop-related methods"""
    
    def test_set_in_loop_default(self):
        """Test default behavior of set_in_loop"""
        node = Node()
        # Should not raise an exception
        node.set_in_loop("loop-1")
        node.set_in_loop(None)
    
    def test_is_in_loop_default(self):
        """Test default behavior of is_in_loop"""
        node = Node()
        result = node.is_in_loop()
        assert result is False


@pytest.mark.unit
class TestNodeStubMethods:
    """Test Node stub methods that return None"""
    
    def test_resurrect_default(self):
        """Test default behavior of resurrect"""
        node = Node()
        result = node.resurrect()
        assert result is None
    
    def test_find_nodes_until_default(self):
        """Test default behavior of _find_nodes_until"""
        node = Node()
        
        # Test with no arguments
        result = node._find_nodes_until(lambda x: True)
        assert result is None
        
        # Test with optional arguments
        result = node._find_nodes_until(
            lambda x: True, 
            skip_node_fn=lambda x: False,
            post_process_fn=lambda x: x
        )
        assert result is None
    
    def test_find_nodes_in_loop_default(self):
        """Test default behavior of find_nodes_in_loop"""
        node = Node()
        result = node.find_nodes_in_loop()
        assert result is None
    
    def test_find_nodes_for_jump_default(self):
        """Test default behavior of find_nodes_for_jump"""
        node = Node()
        result = node.find_nodes_for_jump()
        assert result is None


@pytest.mark.unit 
class TestNodeVariableGeneration:
    """Test Node variable generation logic"""
    
    def test_generate_variables_empty_class(self):
        """Test variable generation for class with no NodeVariableSettings"""
        node = Node()
        
        # Should call _generate_node_variables during __post_init__
        assert isinstance(node.variables, list)
        assert len(node.variables) == 0
    
    def test_generate_variables_with_settings(self):
        """Test variable generation for class with NodeVariableSettings"""
        
        # Create a test node class with variable settings
        class TestNodeWithVars(Node):
            test_var = NodeVariableSettings(
                label="Test Variable",
                default="test_value",
                has_in=True,
                has_out=False
            )
            another_var = NodeVariableSettings(
                label="Another Variable", 
                default=42,
                has_in=False,
                has_out=True
            )
            # Non-NodeVariableSettings attribute (should be ignored)
            regular_attr = "not a variable setting"
        
        with patch.object(NodeVariable, 'create_from_property') as mock_create:
            mock_var1 = Mock(spec=NodeVariable)
            mock_var2 = Mock(spec=NodeVariable)
            mock_create.side_effect = [mock_var1, mock_var2]
            
            node = TestNodeWithVars(id="test")
            
            # Should have called create_from_property twice
            assert mock_create.call_count == 2
            
            # Check the calls
            call_args = mock_create.call_args_list
            assert call_args[0][0][1] == "test_var"  # name argument
            assert call_args[1][0][1] == "another_var"  # name argument
            
            # Should have 2 variables
            assert len(node.variables) == 2
            assert mock_var1 in node.variables
            assert mock_var2 in node.variables
    
    def test_generate_variables_with_attribute_error(self):
        """Test variable generation handles AttributeError gracefully"""
        
        class TestNodeWithErrorVar(Node):
            error_var = NodeVariableSettings(label="Error Variable")
        
        with patch.object(NodeVariable, 'create_from_property') as mock_create:
            mock_create.side_effect = AttributeError("Property cannot be retrieved")
            
            with patch('builtins.print') as mock_print:
                node = TestNodeWithErrorVar(id="test")
                
                # Should have caught the error and printed a message
                mock_print.assert_called_once()
                error_msg = mock_print.call_args[0][0]
                assert "Property 'error_var' can not be retrieved" in error_msg
                assert "TestNodeWithErrorVar" in error_msg
                
                # Should have empty variables list
                assert len(node.variables) == 0
    
    def test_generate_variables_with_path_attributes(self):
        """Test variable generation for nodes with true_path/false_path attributes"""
        
        class TestNodeWithPaths(Node):
            def __init__(self, *args, **kwargs):
                # Set path attributes before calling super().__init__
                self.true_path = "path/to/true"
                self.false_path = "path/to/false"
                super().__init__(*args, **kwargs)
        
        with patch.object(NodeVariable, 'add_path_variable') as mock_add_path:
            mock_var1 = Mock(spec=NodeVariable)
            mock_var2 = Mock(spec=NodeVariable)
            mock_add_path.side_effect = [mock_var1, mock_var2]
            
            node = TestNodeWithPaths(id="test")
            
            # Should have called add_path_variable twice
            assert mock_add_path.call_count == 2
            
            # Check the calls
            call_args = mock_add_path.call_args_list
            assert call_args[0][0][1] == "true_path"
            assert call_args[1][0][1] == "false_path"
            
            # Should have 2 variables
            assert len(node.variables) == 2
            assert mock_var1 in node.variables
            assert mock_var2 in node.variables
    
    def test_generate_variables_path_returns_none(self):
        """Test variable generation when add_path_variable returns None"""
        
        class TestNodeWithPaths(Node):
            def __init__(self, *args, **kwargs):
                self.true_path = "path/to/true"
                super().__init__(*args, **kwargs)
        
        with patch.object(NodeVariable, 'add_path_variable') as mock_add_path:
            mock_add_path.return_value = None  # Simulate returning None
            
            node = TestNodeWithPaths(id="test")
            
            # Should have called add_path_variable
            mock_add_path.assert_called_once()
            
            # Should have empty variables list (None not added)
            assert len(node.variables) == 0


@pytest.mark.unit
class TestNodeFileOperations:
    """Test Node file system operations"""
    
    def test_get_declaring_file_success(self):
        """Test successful file path resolution"""
        node = Node()
        node.path = "os.path.join"  # Use real module for testing
        
        result = node._get_declaring_file()
        
        assert result is not None
        assert isinstance(result, Path)
        assert result.name.endswith(".py")
    
    def test_get_declaring_file_invalid_path(self):
        """Test file path resolution with invalid module path"""
        node = Node()
        node.path = "nonexistent.module.function"
        
        with patch('builtins.print') as mock_print:
            result = node._get_declaring_file()
            
            assert result is None
            mock_print.assert_called_once()
            error_msg = mock_print.call_args[0][0]
            assert "Can't resolve file for nonexistent.module.function" in error_msg
    
    def test_get_declaring_file_empty_path(self):
        """Test file path resolution with empty path"""
        node = Node()
        node.path = ""
        
        with patch('builtins.print') as mock_print:
            result = node._get_declaring_file()
            
            assert result is None
            mock_print.assert_called_once()
    
    @patch('pathlib.Path.read_text')
    @patch('pathlib.Path.exists')
    def test_get_code_success(self, mock_exists, mock_read_text):
        """Test successful code reading"""
        node = Node()
        node.path = "test.module.function"
        
        mock_exists.return_value = True
        mock_read_text.return_value = "def test_function(): pass"
        
        with patch.object(node._file_resolver, 'get_declaring_file') as mock_get_file:
            mock_file = Mock(spec=Path)
            mock_file.exists.return_value = True
            mock_file.read_text.return_value = "def test_function(): pass"
            mock_get_file.return_value = mock_file
            
            result = node._get_code()
            
            assert result == "def test_function(): pass"
            mock_file.read_text.assert_called_once_with(encoding="utf-8")
    
    def test_get_code_file_not_found(self):
        """Test code reading when file doesn't exist"""
        node = Node()
        
        with patch.object(node._file_resolver, 'get_declaring_file') as mock_get_file:
            mock_file = Mock(spec=Path)
            mock_file.exists.return_value = False
            mock_get_file.return_value = mock_file
            
            result = node._get_code()
            
            assert result is None
    
    def test_get_code_no_file_path(self):
        """Test code reading when file path resolution fails"""
        node = Node()
        
        with patch.object(node._file_resolver, 'get_declaring_file') as mock_get_file:
            mock_get_file.return_value = None
            
            result = node._get_code()
            
            assert result is None
    
    def test_get_documentation_success(self):
        """Test successful documentation reading"""
        node = Node()
        
        with patch.object(node._file_resolver, 'get_declaring_file') as mock_get_file:
            mock_file = Mock(spec=Path)
            mock_doc_path = Mock(spec=Path)
            mock_doc_path.exists.return_value = True
            mock_doc_path.read_text.return_value = "# Documentation"
            mock_file.with_name.return_value = mock_doc_path
            mock_file.stem = "module"
            mock_get_file.return_value = mock_file
            
            result = node._get_documentation()
            
            assert result == "# Documentation"
            mock_file.with_name.assert_called_once_with("module_README.md")
            mock_doc_path.read_text.assert_called_once_with(encoding="utf-8")
    
    def test_get_documentation_file_not_found(self):
        """Test documentation reading when README doesn't exist"""
        node = Node()
        
        with patch.object(node._file_resolver, 'get_declaring_file') as mock_get_file:
            mock_file = Mock(spec=Path)
            mock_doc_path = Mock(spec=Path)
            mock_doc_path.exists.return_value = False
            mock_file.with_name.return_value = mock_doc_path
            mock_file.stem = "module"
            mock_get_file.return_value = mock_file
            
            result = node._get_documentation()
            
            assert result is None
    
    def test_get_documentation_no_file_path(self):
        """Test documentation reading when file path resolution fails"""
        node = Node()
        
        with patch.object(node._file_resolver, 'get_declaring_file') as mock_get_file:
            mock_get_file.return_value = None
            
            result = node._get_documentation()
            
            assert result is None
    
    def test_get_icon_content_no_icon(self):
        """Test icon content when no icon is set"""
        node = Node()
        node.icon = ""
        
        result = node._get_icon_content()
        
        assert result == ""
    
    def test_get_icon_content_success(self):
        """Test successful icon content reading"""
        node = Node()
        node.icon = "test-icon.svg"
        
        with patch.object(node._file_resolver, 'get_declaring_file') as mock_get_file:
            mock_file = Mock(spec=Path)
            mock_icon_path = Mock(spec=Path)
            mock_icon_path.exists.return_value = True
            mock_icon_path.read_text.return_value = "<svg>icon content</svg>"
            
            # Mock the Path division operation correctly
            mock_parent = Mock()
            mock_icons_dir = Mock()
            mock_parent.__truediv__ = Mock(return_value=mock_icons_dir)
            mock_icons_dir.__truediv__ = Mock(return_value=mock_icon_path)
            mock_file.parent = mock_parent
            mock_get_file.return_value = mock_file
            
            result = node._get_icon_content()
            
            assert result == "<svg>icon content</svg>"
            mock_icon_path.read_text.assert_called_once_with(encoding="utf-8")
    
    def test_get_icon_content_file_not_found(self):
        """Test icon content when icon file doesn't exist"""
        node = Node()
        node.icon = "missing-icon.svg"
        
        with patch.object(node._file_resolver, 'get_declaring_file') as mock_get_file:
            mock_file = Mock(spec=Path)
            mock_icon_path = Mock(spec=Path)
            mock_icon_path.exists.return_value = False
            
            # Mock the Path division operation correctly
            mock_parent = Mock()
            mock_icons_dir = Mock()
            mock_parent.__truediv__ = Mock(return_value=mock_icons_dir)
            mock_icons_dir.__truediv__ = Mock(return_value=mock_icon_path)
            mock_file.parent = mock_parent
            mock_get_file.return_value = mock_file
            
            result = node._get_icon_content()
            
            # Should return the icon string itself
            assert result == "missing-icon.svg"
    
    def test_get_icon_content_no_file_path(self):
        """Test icon content when file path resolution fails"""
        node = Node()
        node.icon = "test-icon.svg"
        
        with patch.object(node._file_resolver, 'get_declaring_file') as mock_get_file:
            mock_get_file.return_value = None
            
            result = node._get_icon_content()
            
            # Should return the icon string itself
            assert result == "test-icon.svg"