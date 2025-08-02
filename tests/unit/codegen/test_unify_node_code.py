import pytest
from polysynergy_node_runner.services.codegen.steps.unify_node_code import unify_node_code


@pytest.mark.unit
class TestUnifyNodeCode:
    
    def test_simple_node_transformation(self):
        code = """import json
from typing import List

@node()
class TestNode(Node):
    def execute(self):
        return "test"
"""
        collected_imports = set()
        
        result = unify_node_code(code, collected_imports)
        
        # Should strip @node decorator, replace Node with ExecutableNode, collect imports
        assert "@node" not in result
        assert "class TestNode(ExecutableNode):" in result
        assert "def execute(self):" in result
        assert 'return "test"' in result
        
        # Imports should be collected
        assert "import json" in collected_imports
        assert "from typing import List" in collected_imports
    
    def test_node_with_version_suffix(self):
        code = """@node()
class TestNode(Node):
    pass
"""
        collected_imports = set()
        version = 1.5
        
        result = unify_node_code(code, collected_imports, version)
        
        # Should add version suffix to class name (format is V1_5, not _v1_5)
        assert "class TestNodeV1_5(ExecutableNode):" in result
        assert "class TestNode(ExecutableNode):" not in result
    
    def test_service_node_transformation(self):
        code = """@node()
class ApiNode(ServiceNode):
    def call_api(self):
        return self.request.get('/api')
"""
        collected_imports = set()
        
        result = unify_node_code(code, collected_imports)
        
        # Should replace ServiceNode with ExecutableNode
        assert "class ApiNode(ExecutableNode):" in result
        assert "ServiceNode" not in result
    
    def test_multiline_decorator_removal(self):
        code = """import os

@node(
    name="test",
    version=1.0,
    category="logic"
)
class TestNode(Node):
    def execute(self):
        return os.getcwd()
"""
        collected_imports = set()
        
        result = unify_node_code(code, collected_imports)
        
        # Should remove entire multiline decorator
        assert "@node" not in result
        assert "name=" not in result
        assert "version=" not in result
        assert "category=" not in result
        assert "class TestNode(ExecutableNode):" in result
        assert "import os" in collected_imports
    
    def test_preserves_non_import_code(self):
        code = """import json

@node()
class TestNode(Node):
    def __init__(self):
        self.data = {}
    
    def execute(self):
        return json.dumps(self.data)
    
    def helper_method(self):
        return "helper"
"""
        collected_imports = set()
        
        result = unify_node_code(code, collected_imports)
        
        # Should preserve all methods and class structure
        assert "def __init__(self):" in result
        assert "self.data = {}" in result
        assert "def execute(self):" in result
        assert "def helper_method(self):" in result
        assert 'return "helper"' in result
    
    def test_version_zero_handling(self):
        code = """@node()
class TestNode(Node):
    pass
"""
        collected_imports = set()
        version = 0.0
        
        result = unify_node_code(code, collected_imports, version)
        
        # Version 0.0 should add V0_0 suffix
        assert "class TestNodeV0_0(ExecutableNode):" in result
    
    def test_version_integer_handling(self):
        code = """@node()
class TestNode(Node):
    pass
"""
        collected_imports = set()
        version = 2
        
        result = unify_node_code(code, collected_imports, version)
        
        # Integer version should work
        assert "class TestNodeV2_0(ExecutableNode):" in result
    
    def test_multiple_classes_with_version(self):
        code = """@node()
class FirstNode(Node):
    pass

@node()
class SecondNode(ServiceNode):
    pass
"""
        collected_imports = set()
        version = 1.1
        
        result = unify_node_code(code, collected_imports, version)
        
        # Both classes should get version suffix
        assert "class FirstNodeV1_1(ExecutableNode):" in result
        assert "class SecondNodeV1_1(ExecutableNode):" in result
    
    def test_preserves_inheritance_with_mixins(self):
        code = """@node()
class TestNode(Node, SomeMixin):
    pass
"""
        collected_imports = set()
        
        result = unify_node_code(code, collected_imports)
        
        # The replace function only replaces exact matches "(Node):" not "(Node,"
        # So this should remain unchanged
        assert "class TestNode(Node, SomeMixin):" in result
    
    def test_handles_complex_imports(self):
        code = """import os
import sys
from typing import List, Dict, Optional
from polysynergy_node_runner.node_variable_settings import NodeVariable
from custom_module import helper

@node()
class TestNode(Node):
    pass
"""
        collected_imports = set()
        
        result = unify_node_code(code, collected_imports)
        
        # Should collect most imports but skip excluded ones
        expected_imports = {
            "import os",
            "import sys", 
            "from typing import List, Dict, Optional",
            "from custom_module import helper"
        }
        assert collected_imports == expected_imports
        
        # Should not contain excluded import in result
        assert "node_variable_settings" not in result
    
    def test_empty_code_handling(self):
        code = ""
        collected_imports = set()
        
        result = unify_node_code(code, collected_imports)
        
        assert result == ""
        assert len(collected_imports) == 0
    
    def test_code_without_decorator(self):
        code = """import json

class RegularClass:
    def method(self):
        return "test"
"""
        collected_imports = set()
        
        result = unify_node_code(code, collected_imports)
        
        # Should still collect imports and do other transformations
        assert "import json" in collected_imports
        assert "class RegularClass:" in result
        assert "def method(self):" in result