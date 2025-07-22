import re

def strip_single_line_nodevar(line):
    line = re.sub(r'dock_property\s*\([^)]*\)', '', line)

    mdef = re.search(r'default\s*=\s*([^,\)\s]+)', line)
    if mdef:
        default_val = mdef.group(1).strip()
    else:
        default_val = "None"

    pat = re.compile(
        r'^(\s*)'
        r'(\w+)\s*'
        r':\s*([^=]+)\s*'
        r'=\s*(?:NodeVariableSettings|PathSettings)\s*\(.*\)$',
        re.DOTALL
    )
    mm = pat.match(line)
    if mm:
        indent = mm.group(1)
        varname = mm.group(2)
        vartype = mm.group(3).strip()
        return f"{indent}{varname}: {vartype} = {default_val}"
    else:
        return line