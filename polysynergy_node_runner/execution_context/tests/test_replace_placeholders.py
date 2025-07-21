import json

from polysynergy_node_runner.execution_context.replace_placeholders import replace_placeholders


def test_simple_field_replacement():
    template = {
        "full_name": "{{ user.first_name }} {{ user.last_name }}"
    }

    values = {
        "user": {
            "first_name": "Dion",
            "last_name": "Snoeijen"
        }
    }

    result = replace_placeholders(template, values)

    assert result == {
        "full_name": "Dion Snoeijen"
    }

def test_array_indexing():
    template = {
        "first": "{{ items[0].name }}",
        "second": "{{ items[1].name }}"
    }

    values = {
        "items": [
            {"name": "Alpha"},
            {"name": "Beta"}
        ]
    }

    result = replace_placeholders(template, values)

    assert result == {
        "first": "Alpha",
        "second": "Beta"
    }

def test_full_json_injection():
    template = '''
    {
        "copy": {{ user | tojson }}
    }
    '''

    values = {
        "user": {
            "name": "Dion",
            "role": "CTO"
        }
    }

    result = json.loads(replace_placeholders(template, values))

    assert result == {
        "copy": {
            "name": "Dion",
            "role": "CTO"
        }
    }

def test_error_on_missing_field():
    template = {
        "boom": "{{ does_not_exist }}"
    }

    try:
        replace_placeholders(template, {})
    except Exception as e:
        assert "does_not_exist" in str(e)
    else:
        assert False, "Expected error for missing field"

if __name__ == "__main__":
    test_simple_field_replacement()
    test_array_indexing()
    test_full_json_injection()
    test_error_on_missing_field()
    print("✅ All tests passed.")