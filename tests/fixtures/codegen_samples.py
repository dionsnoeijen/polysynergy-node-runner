"""
Test fixtures for codegen testing.
Contains sample JSON workflows and expected code snippets.
"""

# Simple single node workflow
SIMPLE_NODE_WORKFLOW = {
    "nodes": [
        {
            "id": "node-1",
            "handle": "test_node",
            "path": "test.nodes.TestNode",
            "type": "logic",
            "category": "logic",
            "stateful": True,
            "version": 1.0,
            "code": '''import json
from typing import Dict

@node(
    name="Test Node",
    category="logic"
)
class TestNode(Node):
    def execute(self) -> Dict:
        return {"message": "Hello from test node", "data": json.dumps({"test": True})}
'''
        }
    ],
    "connections": []
}

# Workflow with two connected nodes
CONNECTED_NODES_WORKFLOW = {
    "nodes": [
        {
            "id": "input-node",
            "handle": "input_node", 
            "path": "test.nodes.InputNode",
            "type": "input",
            "category": "input",
            "version": 1.0,
            "code": '''@node()
class InputNode(Node):
    def execute(self):
        return {"value": 42}
'''
        },
        {
            "id": "output-node",
            "handle": "output_node",
            "path": "test.nodes.OutputNode", 
            "type": "output",
            "category": "output",
            "version": 1.0,
            "code": '''@node()
class OutputNode(Node):
    def execute(self):
        input_data = self.get_input("data")
        return {"result": input_data.get("value", 0) * 2}
'''
        }
    ],
    "connections": [
        {
            "id": "conn-1",
            "sourceNodeId": "input-node",
            "sourceHandle": "output",
            "targetNodeId": "output-node", 
            "targetHandle": "data"
        }
    ]
}

# Workflow with group nodes
GROUP_WORKFLOW = {
    "nodes": [
        {
            "id": "group-1",
            "handle": "processing_group",
            "type": "group",
            "category": "group"
        },
        {
            "id": "node-in-group",
            "handle": "processor",
            "path": "test.nodes.ProcessorNode",
            "type": "logic",
            "category": "logic",
            "code": '''@node()
class ProcessorNode(Node):
    def execute(self):
        return {"processed": True}
'''
        },
        {
            "id": "external-node",
            "handle": "external",
            "path": "test.nodes.ExternalNode", 
            "type": "output",
            "category": "output",
            "code": '''@node()
class ExternalNode(Node):
    def execute(self):
        return {"external": True}
'''
        }
    ],
    "connections": [
        {
            "id": "conn-1",
            "sourceNodeId": "node-in-group",
            "sourceGroupId": "group-1",
            "sourceHandle": "output",
            "targetNodeId": "external-node",
            "targetGroupId": None,
            "targetHandle": "input"
        }
    ]
}

# Complex workflow with multiple versions and service nodes
COMPLEX_WORKFLOW = {
    "nodes": [
        {
            "id": "api-node",
            "handle": "api_client",
            "path": "test.services.ApiClient",
            "type": "service", 
            "category": "service",
            "version": 2.1,
            "code": '''import requests
from typing import Optional

@node(name="API Client")
class ApiClient(ServiceNode):
    def execute(self) -> Optional[dict]:
        try:
            response = requests.get("https://api.example.com/data")
            return response.json()
        except Exception as e:
            return {"error": str(e)}
'''
        },
        {
            "id": "transform-node",
            "handle": "transformer",
            "path": "test.nodes.DataTransformer",
            "type": "logic",
            "category": "logic", 
            "version": 1.0,
            "flowState": "enabled",
            "code": '''from typing import Any, Dict

@node()
class DataTransformer(Node):
    def execute(self) -> Dict[str, Any]:
        api_data = self.get_input("api_data")
        if api_data and "error" not in api_data:
            return {
                "transformed": True,
                "count": len(api_data.get("items", [])),
                "summary": "Data processed successfully"
            }
        return {"transformed": False, "error": "No valid data to transform"}
'''
        }
    ],
    "connections": [
        {
            "id": "api-to-transform",
            "sourceNodeId": "api-node",
            "sourceHandle": "data",
            "targetNodeId": "transform-node",
            "targetHandle": "api_data"
        }
    ]
}

# Workflow with mock nodes
MOCK_WORKFLOW = {
    "nodes": [
        {
            "id": "mock-node",
            "handle": "mock_input",
            "path": "test.mocks.MockInput",
            "type": "mock",
            "category": "mock",
            "code": '''@node()
class MockInput(Node):
    def execute(self):
        return {"mock_data": "test"}
'''
        },
        {
            "id": "real-node",
            "handle": "real_processor", 
            "path": "test.nodes.RealProcessor",
            "type": "logic",
            "category": "logic",
            "code": '''@node()
class RealProcessor(Node):
    def execute(self):
        return {"processed": True}
'''
        }
    ],
    "connections": [
        {
            "id": "mock-to-real",
            "sourceNodeId": "mock-node",
            "sourceHandle": "output",
            "targetNodeId": "real-node",
            "targetHandle": "input"
        }
    ]
}

# Expected code patterns to check for in generated output
EXPECTED_PATTERNS = {
    "header": [
        "#!/usr/bin/env python3",
        "import types",
        "import logging", 
        "import uuid",
        "import asyncio",
        "from polysynergy_node_runner.execution_context.flow import Flow"
    ],
    "lambda_handler": [
        "def lambda_handler(event, context):",
        "stage = event.get(\"stage\", \"mock\")",
        "node_id = event.get(\"node_id\")",
        "run_id = str(uuid.uuid4())"
    ],
    "execution_environment": [
        "def create_execution_environment(mock = False, run_id:str = \"\", stage:str=None, sub_stage:str=None):",
        "storage.clear_previous_execution(NODE_SETUP_VERSION_ID)",
        "node_context = Context("
    ]
}