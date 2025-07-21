from services.codegen.steps.strip_multiline_nodevar import strip_multiline_nodevar
from services.codegen.steps.is_single_line_node_var import is_single_line_nodevar
from services.codegen.steps.strip_single_line_nodevar import strip_single_line_nodevar


def strip_nodevariable_all(lines):
    tmp = []
    for line in lines:
        if is_single_line_nodevar(line):
            tmp.append(strip_single_line_nodevar(line))
        else:
            tmp.append(line)
    return list(strip_multiline_nodevar(tmp))