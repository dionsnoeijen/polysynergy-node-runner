MAX_PREVIEW_SIZE = 16384 * 4 # 64KB

def truncate_large_values(obj):
    if isinstance(obj, dict):
        return {k: truncate_large_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [truncate_large_values(v) for v in obj]
    elif isinstance(obj, (str, bytes)) and len(obj) > MAX_PREVIEW_SIZE:
        return f"<truncated {len(obj)} bytes>"
    return obj