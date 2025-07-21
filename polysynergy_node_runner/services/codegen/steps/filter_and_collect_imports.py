import re

def filter_and_collect_imports(lines, collected_imports):
    out = []
    import_pat = re.compile(r'^(from|import)\s+')
    skip_starts = (
        "from polysynergy_node_runner.node_variable_settings",
        "import polysynergy_node_runner.node_variable_settings"
    )
    for line in lines:
        st = line.strip()
        if import_pat.match(st):
            if any(st.startswith(ss) for ss in skip_starts):
                continue
            else:
                collected_imports.add(st)
        else:
            out.append(line)
    return out