import re


def strip_multiline_nodevar(lines):
    inside = False
    buffer = []
    paren_count = 0
    indent = ""
    varname = ""
    vartype = ""

    re_start = re.compile(r'^(\s*)(\w+)\s*:\s*([^=]+?)\s*=\s*(?:NodeVariableSettings|PathSettings)\s*\(')

    def flush_buffer():
        full = "\n".join(buffer)
        full = re.sub(r'dock_property\s*\([^)]*\)', '', full, flags=re.DOTALL)
        mdef = re.search(r'default\s*=\s*([^,\)\n]+)', full)
        if mdef:
            df = mdef.group(1).strip()
        else:
            df = "None"
        return f"{indent}{varname}: {vartype} = {df}"

    for line in lines:
        if not inside:
            m = re_start.match(line)
            if m:
                inside = True
                buffer = [line]
                indent = m.group(1)
                varname = m.group(2)
                vartype = m.group(3)
                paren_count = line.count("(") - line.count(")")
            else:
                yield line
        else:
            buffer.append(line)
            paren_count += line.count("(")
            paren_count -= line.count(")")
            if paren_count <= 0:
                yield flush_buffer()
                inside = False
                buffer = []

    if inside and buffer:
        yield flush_buffer()