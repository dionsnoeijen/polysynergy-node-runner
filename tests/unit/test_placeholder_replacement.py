import pytest
from polysynergy_node_runner.execution_context.replace_placeholders import replace_placeholders


@pytest.mark.unit
class TestPlaceholderReplacement:
    
    def test_simple_replacement(self, sample_template_values):
        template = {"greeting": "Hello {{ user.first_name }} {{ user.last_name }}"}
        
        result = replace_placeholders(template, sample_template_values)
        
        assert result == {"greeting": "Hello John Doe"}
    
    def test_array_access(self, sample_template_values):
        template = {
            "first_item": "{{ items[0].name }}",
            "second_item_value": "{{ items[1].value }}"
        }
        
        result = replace_placeholders(template, sample_template_values)
        
        assert result == {
            "first_item": "Item 1",
            "second_item_value": "200"
        }
    
    def test_nested_object_access(self, sample_template_values):
        template = {"api_endpoint": "{{ config.api_url }}/users"}
        
        result = replace_placeholders(template, sample_template_values)
        
        assert result == {"api_endpoint": "https://api.example.com/users"}
    
    def test_complex_template(self, sample_template_values):
        template = {
            "user_info": "{{ user.first_name }} ({{ user.email }})",
            "total_items": "{{ items | length }}",
            "config_timeout": "{{ config.timeout }}"
        }
        
        result = replace_placeholders(template, sample_template_values)
        
        assert result["user_info"] == "John (john.doe@example.com)"
        assert result["config_timeout"] == "30"
    
    def test_missing_variable_raises_error(self):
        template = {"missing": "{{ nonexistent.field }}"}
        
        with pytest.raises(Exception) as exc_info:
            replace_placeholders(template, {})
        
        assert "nonexistent" in str(exc_info.value)
    
    def test_empty_template(self):
        template = {}
        values = {"some": "value"}
        
        result = replace_placeholders(template, values)
        
        assert result == {}
    
    def test_no_placeholders(self, sample_template_values):
        template = {"static": "This has no placeholders"}
        
        result = replace_placeholders(template, sample_template_values)
        
        assert result == {"static": "This has no placeholders"}