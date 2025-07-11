from typing import get_type_hints

def is_compatible_provider(node, expected_type) -> bool:
    try:
        type_hints = get_type_hints(node.provide_instance)
        return_type = type_hints.get('return')
        return isinstance(return_type, type) and issubclass(return_type, expected_type)
    except Exception as e:
        print(f"Can't determine return type of provide_instance: {e}")
        return False