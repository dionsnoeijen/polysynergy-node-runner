import os
import pytest
from unittest.mock import Mock

from polysynergy_node_runner.execution_context.mixins.resolve_environment_variable_mixin import ResolveEnvironmentVariableMixin


class TestEnvironmentVariableReplacement:

    def setup_method(self):
        """Set up test environment."""
        self.original_project_id = os.environ.get("PROJECT_ID")
        os.environ["PROJECT_ID"] = "test-project"

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_project_id:
            os.environ["PROJECT_ID"] = self.original_project_id
        elif "PROJECT_ID" in os.environ:
            del os.environ["PROJECT_ID"]

    def test_replace_environment_placeholders_single(self):
        """Test replacing a single environment placeholder."""

        # Create mock components
        mock_env_vars = Mock()
        mock_env_vars.get_var.return_value = "https://api.openai.com/v1"

        mock_context = Mock()
        mock_context.env_vars = mock_env_vars
        mock_context.get_effective_stage.return_value = "development"

        class TestNode(ResolveEnvironmentVariableMixin):
            def __init__(self):
                self.context = mock_context

        node = TestNode()
        result = node._replace_environment_placeholders("<environment:openai_url>")

        assert result == "https://api.openai.com/v1"
        mock_env_vars.get_var.assert_called_once_with("test-project", "development", "openai_url")

    def test_replace_environment_placeholders_multiple(self):
        """Test replacing multiple environment placeholders in one string."""

        mock_env_vars = Mock()
        def mock_get_var(project_id, stage, key):
            return {
                "api_url": "https://api.example.com",
                "version": "v2.1"
            }.get(key)
        mock_env_vars.get_var.side_effect = mock_get_var

        mock_context = Mock()
        mock_context.env_vars = mock_env_vars
        mock_context.get_effective_stage.return_value = "production"

        class TestNode(ResolveEnvironmentVariableMixin):
            def __init__(self):
                self.context = mock_context

        node = TestNode()
        input_text = "Connect to <environment:api_url> using <environment:version>"
        result = node._replace_environment_placeholders(input_text)

        assert result == "Connect to https://api.example.com using v2.1"

    def test_replace_environment_placeholders_missing_variable(self):
        """Test handling of missing environment variables."""

        mock_env_vars = Mock()
        mock_env_vars.get_var.return_value = None

        mock_context = Mock()
        mock_context.env_vars = mock_env_vars
        mock_context.get_effective_stage.return_value = "development"

        class TestNode(ResolveEnvironmentVariableMixin):
            def __init__(self):
                self.context = mock_context

        node = TestNode()
        result = node._replace_environment_placeholders("<environment:non_existent>")

        assert result == "<ENV_VAR::NOT::FOUND>"

    def test_resolve_environment_variable_with_pattern(self):
        """Test the complete _resolve_environment_variable method with new pattern."""

        mock_env_vars = Mock()
        mock_env_vars.get_var.return_value = "localhost:5432"

        mock_context = Mock()
        mock_context.env_vars = mock_env_vars
        mock_context.get_effective_stage.return_value = "development"

        class TestNode(ResolveEnvironmentVariableMixin):
            database_host: str
            other_field: str

            def __init__(self):
                self.context = mock_context
                self.database_host = "<environment:db_host>"
                self.other_field = "normal_value"

        node = TestNode()
        node._resolve_environment_variable()

        assert node.database_host == "localhost:5432"
        assert node.other_field == "normal_value"  # unchanged

    def test_resolve_environment_variable_existing_functionality(self):
        """Test that existing VariableEnvironment functionality still works."""

        mock_env_vars = Mock()
        mock_env_vars.get_var.return_value = "secret-token-123"

        mock_context = Mock()
        mock_context.env_vars = mock_env_vars
        mock_context.get_effective_stage.return_value = "production"

        class VariableEnvironmentTestNode(ResolveEnvironmentVariableMixin):
            def __init__(self, env_key):
                self.context = mock_context
                self.true_path = env_key

        node = VariableEnvironmentTestNode("API_TOKEN")
        node._resolve_environment_variable()

        assert node.true_path == "secret-token-123"
        mock_env_vars.get_var.assert_called_with("test-project", "production", "API_TOKEN")

    def test_resolve_environment_variable_project_id_missing(self):
        """Test error handling when PROJECT_ID is missing."""

        # Remove PROJECT_ID
        if "PROJECT_ID" in os.environ:
            del os.environ["PROJECT_ID"]

        mock_context = Mock()

        class TestNode(ResolveEnvironmentVariableMixin):
            def __init__(self):
                self.context = mock_context

        node = TestNode()

        with pytest.raises(ValueError, match="PROJECT_ID environment variable is not set"):
            node._replace_environment_placeholders("<environment:test_var>")

    def test_pattern_matching_edge_cases(self):
        """Test edge cases in pattern matching."""

        mock_env_vars = Mock()
        mock_env_vars.get_var.return_value = "test_value"

        mock_context = Mock()
        mock_context.env_vars = mock_env_vars
        mock_context.get_effective_stage.return_value = "test"

        class TestNode(ResolveEnvironmentVariableMixin):
            def __init__(self):
                self.context = mock_context

        node = TestNode()

        # Test with special characters in key
        result = node._replace_environment_placeholders("<environment:test_var-123>")
        assert result == "test_value"

        # Test that malformed patterns are not replaced
        result = node._replace_environment_placeholders("<environment:>")
        assert result == "<environment:>"

        # Test mixed content
        result = node._replace_environment_placeholders("prefix-<environment:test_var-123>-suffix")
        assert result == "prefix-test_value-suffix"