import pytest
from unittest.mock import Mock, patch
from polysynergy_node_runner.services.secrets_manager import get_secrets_manager
from polysynergy_node_runner.services.s3_service import S3Service


@pytest.mark.integration
@pytest.mark.aws
class TestSecretsManager:
    
    @patch('boto3.client')
    def test_get_secrets_manager(self, mock_boto_client):
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        secrets_manager = get_secrets_manager()
        
        assert secrets_manager is not None
        mock_boto_client.assert_called_with('secretsmanager', region_name='eu-central-1')


@pytest.mark.integration
@pytest.mark.aws
class TestS3Service:
    
    @patch('boto3.client')
    def test_s3_service_initialization(self, mock_boto_client):
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        s3_service = S3Service(tenant_id="test-tenant")
        
        assert s3_service is not None
        assert s3_service.tenant_id == "test-tenant"
        mock_boto_client.assert_called_with('s3', region_name='eu-central-1')


@pytest.mark.integration
class TestCodegenService:
    
    def test_build_executable_header(self):
        from polysynergy_node_runner.services.codegen.build_executable import HEADER
        
        assert "#!/usr/bin/env python3" in HEADER
        assert "import asyncio" in HEADER
        assert "from polysynergy_node_runner.execution_context.flow import Flow" in HEADER
    
    def test_build_executable_connections(self):
        from polysynergy_node_runner.services.codegen.build_executable import CONNECTIONS
        
        assert "connections = []" in CONNECTIONS
    
    def test_build_executable_initializers(self):
        from polysynergy_node_runner.services.codegen.build_executable import INITIALIZERS
        
        assert 'execution_flow = {"nodes_order": [], "connections": []}' in INITIALIZERS
        assert "state = ExecutionState()" in INITIALIZERS
        assert "flow = Flow(connections, state, execution_flow)" in INITIALIZERS