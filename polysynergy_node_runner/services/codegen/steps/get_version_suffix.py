def get_version_suffix(version: str | float | int) -> str:
    version_str = str(version)
    parts = version_str.split(".")
    major = parts[0]
    minor = parts[1] if len(parts) > 1 else "0"
    return f"V{major}_{minor}"