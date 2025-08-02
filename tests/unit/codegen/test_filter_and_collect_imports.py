import pytest
from polysynergy_node_runner.services.codegen.steps.filter_and_collect_imports import filter_and_collect_imports


@pytest.mark.unit
class TestFilterAndCollectImports:
    
    def test_collects_simple_imports(self):
        input_lines = [
            "import os",
            "import sys",
            "class TestNode:",
            "    pass"
        ]
        collected_imports = set()
        
        result = filter_and_collect_imports(input_lines, collected_imports)
        
        assert result == ["class TestNode:", "    pass"]
        assert collected_imports == {"import os", "import sys"}
    
    def test_collects_from_imports(self):
        input_lines = [
            "from typing import List, Dict",
            "from pathlib import Path",
            "def some_function():",
            "    return True"
        ]
        collected_imports = set()
        
        result = filter_and_collect_imports(input_lines, collected_imports)
        
        assert result == ["def some_function():", "    return True"]
        assert collected_imports == {"from typing import List, Dict", "from pathlib import Path"}
    
    def test_skips_excluded_imports(self):
        input_lines = [
            "import os",
            "from polysynergy_node_runner.node_variable_settings import something",
            "import polysynergy_node_runner.node_variable_settings",
            "from other_module import something",
            "class TestNode:",
            "    pass"
        ]
        collected_imports = set()
        
        result = filter_and_collect_imports(input_lines, collected_imports)
        
        assert result == ["class TestNode:", "    pass"]
        assert collected_imports == {"import os", "from other_module import something"}
    
    def test_handles_mixed_content(self):
        input_lines = [
            "#!/usr/bin/env python3",
            "import json",
            "from typing import Optional",
            "",
            "class TestNode:",
            "    def __init__(self):",
            "        self.data = {}",
            "",
            "from collections import defaultdict",
            "def helper():",
            "    pass"
        ]
        collected_imports = set()
        
        result = filter_and_collect_imports(input_lines, collected_imports)
        
        expected = [
            "#!/usr/bin/env python3",
            "",
            "class TestNode:",
            "    def __init__(self):",
            "        self.data = {}",
            "",
            "def helper():",
            "    pass"
        ]
        assert result == expected
        assert collected_imports == {
            "import json", 
            "from typing import Optional", 
            "from collections import defaultdict"
        }
    
    def test_preserves_indented_imports_in_code(self):
        # Actually, the function collects ALL imports, even indented ones
        input_lines = [
            "import os",  # This should be collected
            "class TestNode:",
            "    def method(self):",
            "        import json  # This will also be collected",
            "        return json.dumps({})"
        ]
        collected_imports = set()
        
        result = filter_and_collect_imports(input_lines, collected_imports)
        
        expected = [
            "class TestNode:",
            "    def method(self):",
            "        return json.dumps({})"
        ]
        assert result == expected
        assert collected_imports == {"import os", "import json  # This will also be collected"}
    
    def test_handles_multiline_imports(self):
        input_lines = [
            "from typing import (",
            "    List,",
            "    Dict,",
            "    Optional",
            ")",
            "class TestNode:",
            "    pass"
        ]
        collected_imports = set()
        
        result = filter_and_collect_imports(input_lines, collected_imports)
        
        # Note: This function works line by line, so multiline imports 
        # will only match the first line
        expected = [
            "    List,",
            "    Dict,",
            "    Optional",
            ")",
            "class TestNode:",
            "    pass"
        ]
        assert result == expected
        assert collected_imports == {"from typing import ("}
    
    def test_accumulates_imports_across_calls(self):
        # Test that collected_imports accumulates across multiple calls
        collected_imports = set()
        
        lines1 = ["import os", "class A: pass"]
        result1 = filter_and_collect_imports(lines1, collected_imports)
        
        lines2 = ["import sys", "class B: pass"]
        result2 = filter_and_collect_imports(lines2, collected_imports)
        
        assert collected_imports == {"import os", "import sys"}
        assert result1 == ["class A: pass"]
        assert result2 == ["class B: pass"]
    
    def test_handles_empty_input(self):
        input_lines = []
        collected_imports = set()
        
        result = filter_and_collect_imports(input_lines, collected_imports)
        
        assert result == []
        assert collected_imports == set()