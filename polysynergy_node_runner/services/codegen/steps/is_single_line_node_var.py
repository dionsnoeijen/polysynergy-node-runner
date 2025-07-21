def is_single_line_nodevar(line):
    return any(
        sig in line and (line.count("(") == line.count(")"))
        for sig in ["NodeVariableSettings(", "PathSettings("]
    )