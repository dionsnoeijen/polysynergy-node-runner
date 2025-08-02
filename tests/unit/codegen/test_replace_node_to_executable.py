import pytest
from polysynergy_node_runner.services.codegen.steps.replace_node_to_executable import replace_node_to_executable


@pytest.mark.unit
class TestReplaceNodeToExecutable:
    
    def test_replaces_node_inheritance(self):
        input_lines = [
            "class TestNode(Node):",
            "    def execute(self):",
            "        return 'test'"
        ]
        
        result = list(replace_node_to_executable(input_lines))
        
        expected = [
            "class TestNode(ExecutableNode):",
            "    def execute(self):",
            "        return 'test'"
        ]
        assert result == expected
    
    def test_replaces_service_node_inheritance(self):
        input_lines = [
            "class ApiNode(ServiceNode):",
            "    def call_api(self):",
            "        return self.request.get('/api')"
        ]
        
        result = list(replace_node_to_executable(input_lines))
        
        expected = [
            "class ApiNode(ExecutableNode):",
            "    def call_api(self):",
            "        return self.request.get('/api')"
        ]
        assert result == expected
    
    def test_replaces_both_types_in_same_code(self):
        input_lines = [
            "class TestNode(Node):",
            "    pass",
            "",
            "class ApiNode(ServiceNode):",
            "    pass"
        ]
        
        result = list(replace_node_to_executable(input_lines))
        
        expected = [
            "class TestNode(ExecutableNode):",
            "    pass",
            "",
            "class ApiNode(ExecutableNode):",
            "    pass"
        ]
        assert result == expected
    
    def test_preserves_other_inheritance(self):
        input_lines = [
            "class TestNode(ExecutableNode):",
            "    pass",
            "",
            "class Helper(BaseClass):",
            "    pass",
            "",
            "class Another(Node, Mixin):",
            "    pass"
        ]
        
        result = list(replace_node_to_executable(input_lines))
        
        # The function only replaces exact matches "(Node):" and "(ServiceNode):", not "(Node,"
        expected = [
            "class TestNode(ExecutableNode):",
            "    pass",
            "",
            "class Helper(BaseClass):",
            "    pass",
            "",
            "class Another(Node, Mixin):",  # This doesn't get replaced
            "    pass"
        ]
        assert result == expected
    
    def test_handles_whitespace_variations(self):
        input_lines = [
            "class TestNode( Node ):",
            "class AnotherNode(  ServiceNode  ):",
            "class ThirdNode(\tNode\t):"
        ]
        
        result = list(replace_node_to_executable(input_lines))
        
        # Simple string replacement doesn't handle whitespace variations
        # It only replaces exact matches "(Node):" and "(ServiceNode):"
        expected = [
            "class TestNode( Node ):",  # No match due to spaces
            "class AnotherNode(  ServiceNode  ):",  # No match due to spaces  
            "class ThirdNode(\tNode\t):"  # No match due to tabs
        ]
        assert result == expected
    
    def test_no_changes_when_no_match(self):
        input_lines = [
            "def some_function():",
            "    pass",
            "",
            "class RegularClass:",
            "    def method(self):",
            "        return True"
        ]
        
        result = list(replace_node_to_executable(input_lines))
        
        assert result == input_lines
    
    def test_handles_empty_input(self):
        input_lines = []
        
        result = list(replace_node_to_executable(input_lines))
        
        assert result == []