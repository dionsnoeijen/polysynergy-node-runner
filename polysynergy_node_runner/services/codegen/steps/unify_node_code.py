import re

from services.codegen.steps.filter_and_collect_imports import filter_and_collect_imports
from services.codegen.steps.get_version_suffix import get_version_suffix
from services.codegen.steps.replace_node_to_executable import replace_node_to_executable
from services.codegen.steps.strip_multiline_decorator import strip_multiline_decorator
from services.codegen.steps.strip_nodevariable_all import strip_nodevariable_all


def unify_node_code(code, collected_imports, version=None):
    raw_lines = code.splitlines()

    step1 = filter_and_collect_imports(raw_lines, collected_imports)

    step2 = list(strip_multiline_decorator(step1, "@node("))

    step3 = list(replace_node_to_executable(step2))

    step4 = strip_nodevariable_all(step3)

    if version is not None:
        class_def_pat = re.compile(r'^(\s*)class\s+(\w+)\s*\((ExecutableNode)\):')
        version_str = get_version_suffix(version)
        step4 = [
            class_def_pat.sub(rf"\1class \2{version_str}(\3):", line)
            for line in step4
        ]

    return "\n".join(step4)