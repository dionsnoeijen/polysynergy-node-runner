import pytest
from polysynergy_node_runner.services.codegen.steps.strip_multiline_decorator import strip_multiline_decorator


@pytest.mark.unit
class TestStripMultilineDecorator:
    
    def test_strips_simple_single_line_decorator(self):
        input_lines = [
            "    @node()",
            "    class TestNode(Node):",
            "        pass"
        ]
        
        result = list(strip_multiline_decorator(input_lines, "@node("))
        
        expected = [
            "    class TestNode(Node):",
            "        pass"
        ]
        assert result == expected
    
    def test_strips_decorator_with_parameters(self):
        input_lines = [
            "    @node(name='test', version=1.0)",
            "    class TestNode(Node):",
            "        def execute(self):",
            "            return 'test'"
        ]
        
        result = list(strip_multiline_decorator(input_lines, "@node("))
        
        expected = [
            "    class TestNode(Node):",
            "        def execute(self):",
            "            return 'test'"
        ]
        assert result == expected
    
    def test_strips_multiline_decorator(self):
        input_lines = [
            "    @node(",
            "        name='test',",
            "        version=1.0,",
            "        category='test'",
            "    )",
            "    class TestNode(Node):",
            "        pass"
        ]
        
        result = list(strip_multiline_decorator(input_lines, "@node("))
        
        expected = [
            "    class TestNode(Node):",
            "        pass"
        ]
        assert result == expected
    
    def test_handles_nested_parentheses(self):
        input_lines = [
            "    @node(",
            "        config={'nested': {'value': 1}},",
            "        func=lambda x: x * 2",
            "    )",
            "    class TestNode(Node):",
            "        pass"
        ]
        
        result = list(strip_multiline_decorator(input_lines, "@node("))
        
        expected = [
            "    class TestNode(Node):",
            "        pass"
        ]
        assert result == expected
    
    def test_preserves_non_matching_decorators(self):
        input_lines = [
            "    @property",
            "    def value(self):",
            "        return self._value",
            "",
            "    @node()",
            "    class TestNode(Node):",
            "        pass"
        ]
        
        result = list(strip_multiline_decorator(input_lines, "@node("))
        
        expected = [
            "    @property",
            "    def value(self):",
            "        return self._value",
            "",
            "    class TestNode(Node):",
            "        pass"
        ]
        assert result == expected
    
    def test_handles_empty_input(self):
        input_lines = []
        
        result = list(strip_multiline_decorator(input_lines, "@node("))
        
        assert result == []
    
    def test_handles_no_decorator_match(self):
        input_lines = [
            "    class TestNode(Node):",
            "        def execute(self):",
            "            return 'test'"
        ]
        
        result = list(strip_multiline_decorator(input_lines, "@node("))
        
        assert result == input_lines